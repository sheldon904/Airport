"""Event bus service for agent communication."""

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Coroutine
from uuid import UUID

import structlog

from packages.core.config import settings

logger = structlog.get_logger()


class EventBus:
    """
    Event bus for inter-agent communication.

    Supports:
    - Publishing events to topics
    - Subscribing to event types
    - Event history for replay
    - In-memory implementation (can be extended to Redis Streams)
    """

    def __init__(self):
        self.logger = logger.bind(service="event_bus")
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._event_history: list[dict[str, Any]] = []
        self._max_history = 1000

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        transaction_id: UUID | None = None,
        agent_name: str | None = None,
    ) -> None:
        """
        Publish an event to the bus.

        Args:
            event_type: Type of event (e.g., "document.uploaded", "deadline.approaching")
            payload: Event data
            transaction_id: Associated transaction ID
            agent_name: Name of the agent publishing the event
        """
        event = {
            "event_type": event_type,
            "payload": payload,
            "transaction_id": str(transaction_id) if transaction_id else None,
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        self.logger.info(
            "event_published",
            event_type=event_type,
            transaction_id=str(transaction_id) if transaction_id else None,
        )

        # Notify subscribers
        await self._notify_subscribers(event_type, event)

    async def _notify_subscribers(
        self,
        event_type: str,
        event: dict[str, Any],
    ) -> None:
        """Notify all subscribers of an event."""
        # Direct subscribers
        for handler in self._subscribers.get(event_type, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self.logger.error(
                    "subscriber_error",
                    event_type=event_type,
                    error=str(e),
                )

        # Wildcard subscribers (e.g., "document.*")
        prefix = event_type.split(".")[0] + ".*"
        for handler in self._subscribers.get(prefix, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self.logger.error(
                    "subscriber_error",
                    event_type=event_type,
                    pattern=prefix,
                    error=str(e),
                )

        # Global subscribers
        for handler in self._subscribers.get("*", []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self.logger.error(
                    "subscriber_error",
                    event_type=event_type,
                    pattern="*",
                    error=str(e),
                )

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to (supports wildcards like "document.*")
            handler: Async or sync function to handle events
        """
        self._subscribers[event_type].append(handler)
        self.logger.info(
            "subscriber_added",
            event_type=event_type,
        )

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable,
    ) -> None:
        """Unsubscribe from an event type."""
        if handler in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(handler)

    def get_history(
        self,
        event_type: str | None = None,
        transaction_id: UUID | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get event history.

        Args:
            event_type: Filter by event type
            transaction_id: Filter by transaction ID
            limit: Maximum number of events to return
        """
        events = self._event_history

        if event_type:
            events = [e for e in events if e["event_type"] == event_type]

        if transaction_id:
            tid = str(transaction_id)
            events = [e for e in events if e["transaction_id"] == tid]

        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history = []


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the event bus (for testing)."""
    global _event_bus
    _event_bus = None


# Event types
class EventTypes:
    """Standard event type constants."""

    # Document events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSING = "document.processing"
    DOCUMENT_EXTRACTED = "document.extracted"
    DOCUMENT_NEEDS_REVIEW = "document.needs_review"
    DOCUMENT_VERIFIED = "document.verified"
    DOCUMENT_REJECTED = "document.rejected"

    # Deadline events
    DEADLINE_CREATED = "deadline.created"
    DEADLINE_APPROACHING = "deadline.approaching"
    DEADLINE_URGENT = "deadline.urgent"
    DEADLINE_COMPLETED = "deadline.completed"
    DEADLINE_OVERDUE = "deadline.overdue"

    # Transaction events
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_STATUS_CHANGED = "transaction.status_changed"
    TRANSACTION_CLOSING_SOON = "transaction.closing_soon"

    # Checklist events
    CHECKLIST_INITIALIZED = "checklist.initialized"
    CHECKLIST_ITEM_UPDATED = "checklist.item_updated"
    CHECKLIST_COMPLETED = "checklist.completed"

    # Communication events
    COMMUNICATION_DRAFTED = "communication.drafted"
    COMMUNICATION_APPROVED = "communication.approved"
    COMMUNICATION_SENT = "communication.sent"

    # Notification events
    NOTIFICATION_QUEUED = "notification.queued"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_REVIEW_REQUIRED = "agent.review_required"
