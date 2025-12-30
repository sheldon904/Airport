"""Unit tests for real-time/SSE service."""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4

from services.api.routers.realtime import (
    ConnectionManager,
    SSEEventType,
    notify_document_progress,
    notify_document_complete,
    notify_transaction_update,
    notify_deadline_alert,
)


class TestConnectionManager:
    """Tests for ConnectionManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh connection manager."""
        return ConnectionManager()

    def test_create_sse_queue(self, manager):
        """Creates an SSE queue for a user."""
        user_id = str(uuid4())
        org_id = str(uuid4())

        queue = manager.create_sse_queue(user_id, org_id)

        assert queue is not None
        assert isinstance(queue, asyncio.Queue)
        key = f"{org_id}:{user_id}"
        assert key in manager.sse_queues
        assert queue in manager.sse_queues[key]

    def test_remove_sse_queue(self, manager):
        """Removes an SSE queue."""
        user_id = str(uuid4())
        org_id = str(uuid4())

        queue = manager.create_sse_queue(user_id, org_id)
        manager.remove_sse_queue(queue, user_id, org_id)

        key = f"{org_id}:{user_id}"
        assert queue not in manager.sse_queues.get(key, [])

    @pytest.mark.asyncio
    async def test_broadcast_to_org(self, manager):
        """Broadcasts to all connections in an org."""
        org_id = str(uuid4())
        user1_id = str(uuid4())
        user2_id = str(uuid4())

        queue1 = manager.create_sse_queue(user1_id, org_id)
        queue2 = manager.create_sse_queue(user2_id, org_id)

        await manager.broadcast_to_org(
            org_id,
            "test.event",
            {"message": "Hello"}
        )

        # Both queues should have received the message
        msg1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        msg2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

        assert msg1["event"] == "test.event"
        assert msg2["event"] == "test.event"
        assert msg1["data"]["message"] == "Hello"

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager):
        """Sends to a specific user only."""
        org_id = str(uuid4())
        user1_id = str(uuid4())
        user2_id = str(uuid4())

        queue1 = manager.create_sse_queue(user1_id, org_id)
        queue2 = manager.create_sse_queue(user2_id, org_id)

        await manager.send_to_user(
            org_id,
            user1_id,
            "private.event",
            {"secret": "data"}
        )

        # Only user1 should receive
        msg1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        assert msg1["event"] == "private.event"

        # user2's queue should be empty
        assert queue2.empty()


class TestSSEEventTypes:
    """Tests for SSE event type constants."""

    def test_document_events_defined(self):
        """Document event types are defined."""
        assert SSEEventType.DOCUMENT_UPLOAD_STARTED == "document.upload.started"
        assert SSEEventType.DOCUMENT_PROCESSING == "document.processing"
        assert SSEEventType.DOCUMENT_EXTRACTION_PROGRESS == "document.extraction.progress"
        assert SSEEventType.DOCUMENT_EXTRACTION_COMPLETE == "document.extraction.complete"
        assert SSEEventType.DOCUMENT_NEEDS_REVIEW == "document.needs_review"

    def test_transaction_events_defined(self):
        """Transaction event types are defined."""
        assert SSEEventType.TRANSACTION_UPDATED == "transaction.updated"
        assert SSEEventType.TRANSACTION_HEALTH_CHANGED == "transaction.health.changed"

    def test_deadline_events_defined(self):
        """Deadline event types are defined."""
        assert SSEEventType.DEADLINE_APPROACHING == "deadline.approaching"
        assert SSEEventType.DEADLINE_OVERDUE == "deadline.overdue"


class TestNotificationHelpers:
    """Tests for notification helper functions."""

    @pytest.mark.asyncio
    async def test_notify_document_progress(self):
        """Notifies of document processing progress."""
        # This just tests that the function doesn't raise
        await notify_document_progress(
            org_id=uuid4(),
            document_id=uuid4(),
            transaction_id=uuid4(),
            status="processing",
            progress=50,
            message="Extracting data...",
        )

    @pytest.mark.asyncio
    async def test_notify_document_complete(self):
        """Notifies of document extraction completion."""
        await notify_document_complete(
            org_id=uuid4(),
            document_id=uuid4(),
            transaction_id=uuid4(),
            document_type="contract",
            confidence=0.95,
            needs_review=False,
        )

    @pytest.mark.asyncio
    async def test_notify_transaction_update(self):
        """Notifies of transaction updates."""
        await notify_transaction_update(
            org_id=uuid4(),
            transaction_id=uuid4(),
            update_type="status_change",
            data={"new_status": "active"},
        )

    @pytest.mark.asyncio
    async def test_notify_deadline_alert(self):
        """Notifies of deadline alerts."""
        await notify_deadline_alert(
            org_id=uuid4(),
            transaction_id=uuid4(),
            deadline_id=uuid4(),
            deadline_name="Inspection Period",
            due_date="2024-02-15",
            is_overdue=False,
        )
