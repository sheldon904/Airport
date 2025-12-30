"""Real-time updates via Server-Sent Events (SSE) and WebSocket."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.api.dependencies import CurrentUserDep
from packages.core.services.events import get_event_bus, EventTypes

# Configure structured logger for realtime module
logger = logging.getLogger(__name__)

router = APIRouter()


# === Connection Management ===


class ConnectionManager:
    """Manage WebSocket and SSE connections."""

    def __init__(self):
        # WebSocket connections by user/org
        self.active_connections: dict[str, list[WebSocket]] = {}
        # SSE subscriptions by user/org with timestamps
        self.sse_queues: dict[str, list[tuple[asyncio.Queue, float]]] = {}
        # Maximum age for SSE queues (2 hours) - cleanup stale connections
        self._max_queue_age = 7200

    async def connect_ws(self, websocket: WebSocket, user_id: str, org_id: str):
        """Accept a WebSocket connection."""
        await websocket.accept()
        key = f"{org_id}:{user_id}"
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append(websocket)

    def disconnect_ws(self, websocket: WebSocket, user_id: str, org_id: str):
        """Remove a WebSocket connection."""
        key = f"{org_id}:{user_id}"
        if key in self.active_connections:
            if websocket in self.active_connections[key]:
                self.active_connections[key].remove(websocket)
            # Clean up empty lists
            if not self.active_connections[key]:
                del self.active_connections[key]

    def create_sse_queue(self, user_id: str, org_id: str) -> asyncio.Queue:
        """Create an SSE event queue for a user."""
        import time
        key = f"{org_id}:{user_id}"
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)  # Limit queue size to prevent memory issues
        if key not in self.sse_queues:
            self.sse_queues[key] = []
        self.sse_queues[key].append((queue, time.time()))
        # Trigger cleanup of stale connections
        self._cleanup_stale_queues()
        return queue

    def remove_sse_queue(self, queue: asyncio.Queue, user_id: str, org_id: str):
        """Remove an SSE event queue."""
        key = f"{org_id}:{user_id}"
        if key in self.sse_queues:
            self.sse_queues[key] = [
                (q, ts) for q, ts in self.sse_queues[key] if q is not queue
            ]
            # Clean up empty lists
            if not self.sse_queues[key]:
                del self.sse_queues[key]

    def _cleanup_stale_queues(self):
        """Remove SSE queues that have been open too long (possible leak)."""
        import time
        now = time.time()
        keys_to_delete = []

        for key, queue_list in self.sse_queues.items():
            # Filter out stale queues
            fresh_queues = [
                (q, ts) for q, ts in queue_list
                if (now - ts) < self._max_queue_age
            ]
            if fresh_queues:
                self.sse_queues[key] = fresh_queues
            else:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.sse_queues[key]

    def get_connection_stats(self) -> dict[str, int]:
        """Get connection statistics for monitoring."""
        ws_count = sum(len(conns) for conns in self.active_connections.values())
        sse_count = sum(len(queues) for queues in self.sse_queues.values())
        return {
            "websocket_connections": ws_count,
            "sse_connections": sse_count,
            "unique_users": len(self.active_connections) + len(self.sse_queues),
        }

    async def broadcast_to_org(self, org_id: str, event_type: str, data: dict[str, Any]):
        """Broadcast an event to all connections in an organization."""
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Send to WebSocket connections
        failed_connections: list[tuple[str, WebSocket]] = []
        for key, connections in self.active_connections.items():
            if key.startswith(f"{org_id}:"):
                for connection in connections:
                    try:
                        await connection.send_json(message)
                    except WebSocketDisconnect:
                        # Client disconnected - mark for cleanup
                        failed_connections.append((key, connection))
                        logger.debug(
                            "websocket_client_disconnected",
                            extra={"org_id": org_id, "connection_key": key}
                        )
                    except Exception as e:
                        # Log unexpected errors with context
                        logger.warning(
                            "websocket_send_failed",
                            extra={
                                "org_id": org_id,
                                "connection_key": key,
                                "error_type": type(e).__name__,
                                "error": str(e),
                            }
                        )
                        failed_connections.append((key, connection))

        # Clean up failed connections
        for key, connection in failed_connections:
            if key in self.active_connections and connection in self.active_connections[key]:
                self.active_connections[key].remove(connection)

        # Send to SSE queues (now stored as tuples with timestamps)
        for key, queue_list in self.sse_queues.items():
            if key.startswith(f"{org_id}:"):
                for queue, _ in queue_list:
                    try:
                        # Use put_nowait to avoid blocking; queue has maxsize
                        queue.put_nowait(message)
                    except asyncio.QueueFull:
                        # Log when queue is full - client not consuming fast enough (REM-015)
                        logger.warning(
                            "sse_queue_full_message_dropped",
                            extra={
                                "org_id": org_id,
                                "connection_key": key,
                                "event_type": event_type,
                                "queue_size": queue.qsize(),
                            }
                        )
                    except Exception as e:
                        # Log unexpected SSE queue errors
                        logger.error(
                            "sse_queue_error",
                            extra={
                                "org_id": org_id,
                                "connection_key": key,
                                "error_type": type(e).__name__,
                                "error": str(e),
                            }
                        )

    async def send_to_user(self, org_id: str, user_id: str, event_type: str, data: dict[str, Any]):
        """Send an event to a specific user."""
        key = f"{org_id}:{user_id}"
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Send to WebSocket connections
        if key in self.active_connections:
            failed_connections: list[WebSocket] = []
            for connection in self.active_connections[key]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    failed_connections.append(connection)
                    logger.debug(
                        "websocket_client_disconnected_user",
                        extra={"org_id": org_id, "user_id": user_id}
                    )
                except Exception as e:
                    logger.warning(
                        "websocket_send_to_user_failed",
                        extra={
                            "org_id": org_id,
                            "user_id": user_id,
                            "error_type": type(e).__name__,
                            "error": str(e),
                        }
                    )
                    failed_connections.append(connection)

            # Clean up failed connections
            for connection in failed_connections:
                if connection in self.active_connections[key]:
                    self.active_connections[key].remove(connection)

        # Send to SSE queues (now stored as tuples with timestamps)
        if key in self.sse_queues:
            for queue, _ in self.sse_queues[key]:
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    # Log dropped message for monitoring (REM-015)
                    logger.warning(
                        "sse_queue_full_user_message_dropped",
                        extra={
                            "org_id": org_id,
                            "user_id": user_id,
                            "event_type": event_type,
                            "queue_size": queue.qsize(),
                        }
                    )
                except Exception as e:
                    logger.error(
                        "sse_queue_user_error",
                        extra={
                            "org_id": org_id,
                            "user_id": user_id,
                            "error_type": type(e).__name__,
                            "error": str(e),
                        }
                    )


# Global connection manager
manager = ConnectionManager()


# === SSE Event Types ===


class SSEEventType:
    """SSE event type constants."""

    # Document events
    DOCUMENT_UPLOAD_STARTED = "document.upload.started"
    DOCUMENT_PROCESSING = "document.processing"
    DOCUMENT_EXTRACTION_PROGRESS = "document.extraction.progress"
    DOCUMENT_EXTRACTION_COMPLETE = "document.extraction.complete"
    DOCUMENT_EXTRACTION_FAILED = "document.extraction.failed"
    DOCUMENT_NEEDS_REVIEW = "document.needs_review"

    # Transaction events
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_HEALTH_CHANGED = "transaction.health.changed"

    # Deadline events
    DEADLINE_APPROACHING = "deadline.approaching"
    DEADLINE_OVERDUE = "deadline.overdue"

    # Checklist events
    CHECKLIST_UPDATED = "checklist.updated"

    # Communication events
    COMMUNICATION_RECEIVED = "communication.received"


# === SSE Endpoints ===


async def event_generator(
    queue: asyncio.Queue,
    user_id: str,
    org_id: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from a queue."""
    try:
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"

        while True:
            try:
                # Wait for events with timeout to send keepalive
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                event_type = message.get("event", "message")
                data = json.dumps(message)
                yield f"event: {event_type}\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive
                yield f"event: keepalive\ndata: {json.dumps({'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        manager.remove_sse_queue(queue, user_id, org_id)


@router.get("/events")
async def sse_events(
    current_user: CurrentUserDep,
    transaction_id: UUID | None = Query(None, description="Filter events for specific transaction"),
):
    """
    Server-Sent Events endpoint for real-time updates.

    Subscribe to real-time events for your organization. Events include:
    - Document processing status updates
    - Transaction health changes
    - Deadline notifications
    - Checklist updates

    Example usage with JavaScript:
    ```javascript
    const eventSource = new EventSource('/api/v1/realtime/events', {
        headers: { 'Authorization': 'Bearer <token>' }
    });

    eventSource.addEventListener('document.extraction.complete', (e) => {
        const data = JSON.parse(e.data);
        console.log('Document extracted:', data);
    });
    ```
    """
    user_id = str(current_user.id)
    org_id = str(current_user.organization_id)

    queue = manager.create_sse_queue(user_id, org_id)

    return StreamingResponse(
        event_generator(queue, user_id, org_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# === WebSocket Endpoints ===


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for bidirectional real-time communication.

    Connect with a valid JWT token to receive real-time updates
    and send messages.

    Message format:
    ```json
    {
        "type": "subscribe",
        "transaction_id": "uuid"
    }
    ```
    """
    # Validate token using AuthService (REM-007: Log all auth failures for security monitoring)
    from packages.core.services.auth import AuthService
    from packages.db.session import get_db_context

    try:
        async with get_db_context() as db:
            auth_service = AuthService(db)
            payload = auth_service.decode_token(token)

            if not payload:
                logger.warning(
                    "websocket_auth_failed_invalid_payload",
                    extra={"reason": "Token decode returned None"}
                )
                await websocket.close(code=4001, reason="Invalid token")
                return

            user_id = payload.get("sub")
            org_id = payload.get("org")

            if not user_id or not org_id:
                logger.warning(
                    "websocket_auth_failed_missing_claims",
                    extra={
                        "has_user_id": bool(user_id),
                        "has_org_id": bool(org_id),
                    }
                )
                await websocket.close(code=4001, reason="Invalid token")
                return
    except Exception as e:
        # Log authentication failures for security monitoring (REM-007)
        logger.warning(
            "websocket_auth_exception",
            extra={
                "error_type": type(e).__name__,
                "error": str(e),
            }
        )
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect_ws(websocket, user_id, org_id)

    try:
        while True:
            data = await websocket.receive_json()

            # Handle subscription requests
            if data.get("type") == "subscribe":
                transaction_id = data.get("transaction_id")
                await websocket.send_json({
                    "type": "subscribed",
                    "transaction_id": transaction_id,
                })

            # Handle ping
            elif data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        manager.disconnect_ws(websocket, user_id, org_id)


# === Helper Functions for Broadcasting ===


async def notify_document_progress(
    org_id: UUID,
    document_id: UUID,
    transaction_id: UUID,
    status: str,
    progress: int = 0,
    message: str | None = None,
):
    """Notify clients of document processing progress."""
    await manager.broadcast_to_org(
        str(org_id),
        SSEEventType.DOCUMENT_EXTRACTION_PROGRESS,
        {
            "document_id": str(document_id),
            "transaction_id": str(transaction_id),
            "status": status,
            "progress": progress,
            "message": message,
        },
    )


async def notify_document_complete(
    org_id: UUID,
    document_id: UUID,
    transaction_id: UUID,
    document_type: str,
    confidence: float | None = None,
    needs_review: bool = False,
):
    """Notify clients that document extraction is complete."""
    event_type = (
        SSEEventType.DOCUMENT_NEEDS_REVIEW
        if needs_review
        else SSEEventType.DOCUMENT_EXTRACTION_COMPLETE
    )

    await manager.broadcast_to_org(
        str(org_id),
        event_type,
        {
            "document_id": str(document_id),
            "transaction_id": str(transaction_id),
            "document_type": document_type,
            "confidence": confidence,
            "needs_review": needs_review,
        },
    )


async def notify_transaction_update(
    org_id: UUID,
    transaction_id: UUID,
    update_type: str,
    data: dict[str, Any],
):
    """Notify clients of transaction updates."""
    await manager.broadcast_to_org(
        str(org_id),
        SSEEventType.TRANSACTION_UPDATED,
        {
            "transaction_id": str(transaction_id),
            "update_type": update_type,
            **data,
        },
    )


async def notify_deadline_alert(
    org_id: UUID,
    transaction_id: UUID,
    deadline_id: UUID,
    deadline_name: str,
    due_date: str,
    is_overdue: bool = False,
):
    """Notify clients of deadline alerts."""
    event_type = (
        SSEEventType.DEADLINE_OVERDUE
        if is_overdue
        else SSEEventType.DEADLINE_APPROACHING
    )

    await manager.broadcast_to_org(
        str(org_id),
        event_type,
        {
            "transaction_id": str(transaction_id),
            "deadline_id": str(deadline_id),
            "deadline_name": deadline_name,
            "due_date": due_date,
            "is_overdue": is_overdue,
        },
    )


# === Integration with Event Bus ===


def setup_event_bus_integration():
    """Set up event bus subscribers for real-time notifications."""
    event_bus = get_event_bus()

    async def on_document_event(event: dict[str, Any]):
        """Handle document events from the event bus."""
        payload = event.get("payload", {})
        org_id = payload.get("organization_id")
        if not org_id:
            return

        event_type = event.get("event_type")
        document_id = payload.get("document_id")
        transaction_id = payload.get("transaction_id")

        if event_type == EventTypes.DOCUMENT_PROCESSING:
            await notify_document_progress(
                UUID(org_id),
                UUID(document_id),
                UUID(transaction_id),
                status="processing",
                progress=10,
                message="Starting document extraction...",
            )
        elif event_type == EventTypes.DOCUMENT_EXTRACTED:
            await notify_document_complete(
                UUID(org_id),
                UUID(document_id),
                UUID(transaction_id),
                document_type=payload.get("document_type", "unknown"),
                confidence=payload.get("confidence"),
                needs_review=payload.get("needs_review", False),
            )

    async def on_deadline_event(event: dict[str, Any]):
        """Handle deadline events from the event bus."""
        payload = event.get("payload", {})
        org_id = payload.get("organization_id")
        if not org_id:
            return

        event_type = event.get("event_type")

        if event_type in [EventTypes.DEADLINE_APPROACHING, EventTypes.DEADLINE_URGENT, EventTypes.DEADLINE_OVERDUE]:
            await notify_deadline_alert(
                UUID(org_id),
                UUID(payload.get("transaction_id")),
                UUID(payload.get("deadline_id")),
                deadline_name=payload.get("deadline_name", ""),
                due_date=payload.get("due_date", ""),
                is_overdue=event_type == EventTypes.DEADLINE_OVERDUE,
            )

    # Subscribe to events
    event_bus.subscribe("document.*", on_document_event)
    event_bus.subscribe("deadline.*", on_deadline_event)


# Initialize event bus integration on module load
setup_event_bus_integration()
