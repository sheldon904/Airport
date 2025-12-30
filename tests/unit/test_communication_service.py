"""Unit tests for communication log service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from packages.core.services.communication_log import (
    CommunicationLogService,
    CommunicationDirection,
    CommunicationChannel,
    CommunicationStatus,
    TOPIC_KEYWORDS,
    get_communication_log_service,
)


class TestCommunicationConstants:
    """Tests for communication constants."""

    def test_direction_constants(self):
        """Direction constants are defined."""
        assert CommunicationDirection.INBOUND == "inbound"
        assert CommunicationDirection.OUTBOUND == "outbound"

    def test_channel_constants(self):
        """Channel constants are defined."""
        assert CommunicationChannel.EMAIL == "email"
        assert CommunicationChannel.PHONE == "phone"
        assert CommunicationChannel.SMS == "sms"

    def test_status_constants(self):
        """Status constants are defined."""
        assert CommunicationStatus.SENT == "sent"
        assert CommunicationStatus.DELIVERED == "delivered"


class TestTopicCategorization:
    """Tests for topic auto-categorization."""

    @pytest.fixture
    def service(self):
        """Create service with mock session."""
        mock_session = MagicMock()
        return CommunicationLogService(mock_session)

    def test_categorize_earnest_money(self, service):
        """Categorizes earnest money communications."""
        topic = service.categorize_communication(
            subject="Deposit Receipt Needed",
            body="Please send the earnest money deposit receipt."
        )
        assert topic == "earnest_money"

    def test_categorize_inspection(self, service):
        """Categorizes inspection communications."""
        topic = service.categorize_communication(
            subject="Inspection Report",
            body="Attached is the home inspection report."
        )
        assert topic == "inspection"

    def test_categorize_appraisal(self, service):
        """Categorizes appraisal communications."""
        topic = service.categorize_communication(
            subject="Appraisal Scheduled",
            body="The property value assessment has been scheduled."
        )
        assert topic == "appraisal"

    def test_categorize_title(self, service):
        """Categorizes title communications."""
        topic = service.categorize_communication(
            subject="Title Commitment",
            body="Please review the title search results."
        )
        assert topic == "title"

    def test_categorize_closing(self, service):
        """Categorizes closing communications."""
        topic = service.categorize_communication(
            subject="Clear to Close",
            body="We have received closing disclosure."
        )
        assert topic == "closing"

    def test_categorize_financing(self, service):
        """Categorizes financing communications."""
        topic = service.categorize_communication(
            subject="Loan Update",
            body="The mortgage pre-approval is ready."
        )
        assert topic == "financing"

    def test_categorize_unknown(self, service):
        """Returns None for unknown topics."""
        topic = service.categorize_communication(
            subject="Hello",
            body="Just checking in about the weather."
        )
        assert topic is None

    def test_categorize_prioritizes_subject(self, service):
        """Subject takes priority over body for categorization."""
        topic = service.categorize_communication(
            subject="Deposit received",
            body="The inspection is tomorrow."
        )
        assert topic == "earnest_money"


class TestCommunicationLogService:
    """Tests for CommunicationLogService methods."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return CommunicationLogService(mock_session)

    @pytest.mark.asyncio
    async def test_log_communication(self, service, mock_session):
        """Logs a communication entry."""
        org_id = uuid4()
        tx_id = uuid4()

        entry = await service.log_communication(
            organization_id=org_id,
            transaction_id=tx_id,
            direction=CommunicationDirection.OUTBOUND,
            sender="agent@example.com",
            recipients=["buyer@example.com"],
            subject="Status Update",
            body="Here's your weekly update.",
        )

        mock_session.add.assert_called_once()
        assert entry.organization_id == org_id
        assert entry.transaction_id == tx_id
        assert entry.direction == CommunicationDirection.OUTBOUND

    @pytest.mark.asyncio
    async def test_log_communication_auto_topic(self, service, mock_session):
        """Auto-categorizes topic when not provided."""
        entry = await service.log_communication(
            organization_id=uuid4(),
            transaction_id=uuid4(),
            direction=CommunicationDirection.INBOUND,
            sender="title@company.com",
            recipients=["agent@example.com"],
            subject="Title Commitment Ready",
            body="The title commitment is attached.",
        )

        assert entry.topic == "title"

    @pytest.mark.asyncio
    async def test_log_communication_with_explicit_topic(self, service, mock_session):
        """Uses explicit topic when provided."""
        entry = await service.log_communication(
            organization_id=uuid4(),
            transaction_id=uuid4(),
            direction=CommunicationDirection.OUTBOUND,
            sender="agent@example.com",
            recipients=["seller@example.com"],
            subject="Hello",
            body="General message.",
            topic="custom_topic",
        )

        assert entry.topic == "custom_topic"

    @pytest.mark.asyncio
    async def test_log_communication_preview_truncation(self, service, mock_session):
        """Body preview is truncated."""
        long_body = "x" * 1000

        entry = await service.log_communication(
            organization_id=uuid4(),
            transaction_id=uuid4(),
            direction=CommunicationDirection.OUTBOUND,
            sender="agent@example.com",
            recipients=["client@example.com"],
            subject="Long message",
            body=long_body,
        )

        assert len(entry.body_preview) <= 500


class TestCommunicationServiceFactory:
    """Tests for service factory."""

    def test_get_communication_log_service(self):
        """Factory returns service instance."""
        mock_session = MagicMock()
        service = get_communication_log_service(mock_session)
        assert isinstance(service, CommunicationLogService)
