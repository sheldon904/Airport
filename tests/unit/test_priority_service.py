"""Unit tests for priority/health scoring service."""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from packages.core.services.priority import (
    PriorityService,
    HealthStatus,
    PriorityLevel,
    HEALTH_WEIGHTS,
    CRITICAL_THRESHOLD,
    ATTENTION_THRESHOLD,
    get_priority_service,
)


class TestHealthStatusConstants:
    """Tests for health status constants."""

    def test_health_statuses_defined(self):
        """Health statuses are defined correctly."""
        assert HealthStatus.ON_TRACK == "on_track"
        assert HealthStatus.ATTENTION == "attention"
        assert HealthStatus.CRITICAL == "critical"


class TestPriorityLevelConstants:
    """Tests for priority level constants."""

    def test_priority_levels_defined(self):
        """Priority levels are defined correctly."""
        assert PriorityLevel.URGENT == "urgent"
        assert PriorityLevel.HIGH == "high"
        assert PriorityLevel.NORMAL == "normal"
        assert PriorityLevel.LOW == "low"


class TestHealthWeights:
    """Tests for health scoring weights."""

    def test_days_to_closing_weights(self):
        """Days to closing weights are configured."""
        assert HEALTH_WEIGHTS["days_to_closing"]["0-3"] == 30
        assert HEALTH_WEIGHTS["days_to_closing"]["4-7"] == 20
        assert HEALTH_WEIGHTS["days_to_closing"]["8-14"] == 10
        assert HEALTH_WEIGHTS["days_to_closing"]["15+"] == 0

    def test_deadline_weights(self):
        """Deadline weights are configured."""
        assert HEALTH_WEIGHTS["overdue_deadline"] == 25
        assert HEALTH_WEIGHTS["due_soon_deadline"] == 10

    def test_document_weights(self):
        """Document weights are configured."""
        assert HEALTH_WEIGHTS["pending_review"] == 10
        assert HEALTH_WEIGHTS["missing_required_doc"] == 15

    def test_communication_weights(self):
        """Communication weights are configured."""
        assert HEALTH_WEIGHTS["stalled_communication"] == 10


class TestThresholds:
    """Tests for health status thresholds."""

    def test_critical_threshold(self):
        """Critical threshold is set."""
        assert CRITICAL_THRESHOLD == 70

    def test_attention_threshold(self):
        """Attention threshold is set."""
        assert ATTENTION_THRESHOLD == 40


class TestPriorityService:
    """Tests for PriorityService methods."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return PriorityService(mock_session)

    def _mock_transaction(self, closing_date=None, priority_score=0, health_status="on_track"):
        """Create a mock transaction object."""
        tx = MagicMock()
        tx.id = uuid4()
        tx.closing_date = closing_date
        tx.priority_score = priority_score
        tx.health_status = health_status
        tx.property_address = {"street": "123 Main St", "city": "Miami"}
        tx.status = "active"
        tx.purchase_price = 350000
        return tx

    @pytest.mark.asyncio
    async def test_calculate_health_no_transaction(self, service, mock_session):
        """Returns default values when transaction not found."""
        # Mock no transaction found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        score, status, issues = await service.calculate_health(uuid4())

        assert score == 0
        assert status == HealthStatus.ON_TRACK
        assert issues == []

    @pytest.mark.asyncio
    async def test_calculate_health_on_track(self, service, mock_session):
        """Transaction with no issues is on track."""
        tx = self._mock_transaction(
            closing_date=date.today() + timedelta(days=30)
        )

        # Mock transaction query
        tx_result = MagicMock()
        tx_result.scalar_one_or_none.return_value = tx

        # Mock count queries all returning 0
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        mock_session.execute.side_effect = [tx_result, count_result, count_result, count_result, count_result]

        score, status, issues = await service.calculate_health(tx.id)

        assert score < ATTENTION_THRESHOLD
        assert status == HealthStatus.ON_TRACK
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_calculate_health_critical_closing_soon(self, service, mock_session):
        """Closing in 3 days or less adds 30 points."""
        tx = self._mock_transaction(
            closing_date=date.today() + timedelta(days=2)
        )

        tx_result = MagicMock()
        tx_result.scalar_one_or_none.return_value = tx

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        mock_session.execute.side_effect = [tx_result, count_result, count_result, count_result, count_result]

        score, status, issues = await service.calculate_health(tx.id)

        assert score >= 30
        assert "Closing in 2 days" in issues[0]

    @pytest.mark.asyncio
    async def test_calculate_health_overdue_deadlines(self, service, mock_session):
        """Overdue deadlines add 25 points each."""
        tx = self._mock_transaction(
            closing_date=date.today() + timedelta(days=30)
        )

        tx_result = MagicMock()
        tx_result.scalar_one_or_none.return_value = tx

        # Mock 3 overdue deadlines
        overdue_result = MagicMock()
        overdue_result.scalar.return_value = 3

        other_result = MagicMock()
        other_result.scalar.return_value = 0

        mock_session.execute.side_effect = [tx_result, overdue_result, other_result, other_result, other_result]

        score, status, issues = await service.calculate_health(tx.id)

        assert score >= 75  # 3 * 25 = 75
        assert status == HealthStatus.CRITICAL
        assert any("overdue" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_calculate_health_due_soon_deadlines(self, service, mock_session):
        """Due soon deadlines add 10 points each."""
        tx = self._mock_transaction(
            closing_date=date.today() + timedelta(days=30)
        )

        tx_result = MagicMock()
        tx_result.scalar_one_or_none.return_value = tx

        overdue_result = MagicMock()
        overdue_result.scalar.return_value = 0

        due_soon_result = MagicMock()
        due_soon_result.scalar.return_value = 4

        other_result = MagicMock()
        other_result.scalar.return_value = 0

        mock_session.execute.side_effect = [tx_result, overdue_result, due_soon_result, other_result, other_result]

        score, status, issues = await service.calculate_health(tx.id)

        assert score >= 40  # 4 * 10 = 40
        assert status == HealthStatus.ATTENTION
        assert any("due within 3 days" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_calculate_health_pending_review(self, service, mock_session):
        """Pending review documents add 10 points each."""
        tx = self._mock_transaction(
            closing_date=date.today() + timedelta(days=30)
        )

        tx_result = MagicMock()
        tx_result.scalar_one_or_none.return_value = tx

        zero_result = MagicMock()
        zero_result.scalar.return_value = 0

        pending_result = MagicMock()
        pending_result.scalar.return_value = 5

        mock_session.execute.side_effect = [tx_result, zero_result, zero_result, pending_result, zero_result]

        score, status, issues = await service.calculate_health(tx.id)

        assert score >= 50  # 5 * 10 = 50
        assert any("need review" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_calculate_health_combined_factors(self, service, mock_session):
        """Multiple factors combine to determine status."""
        tx = self._mock_transaction(
            closing_date=date.today() + timedelta(days=5)  # +20 points
        )

        tx_result = MagicMock()
        tx_result.scalar_one_or_none.return_value = tx

        overdue_result = MagicMock()
        overdue_result.scalar.return_value = 2  # +50 points

        due_soon_result = MagicMock()
        due_soon_result.scalar.return_value = 1  # +10 points

        pending_result = MagicMock()
        pending_result.scalar.return_value = 0

        mock_session.execute.side_effect = [tx_result, overdue_result, due_soon_result, pending_result, pending_result]

        score, status, issues = await service.calculate_health(tx.id)

        assert score >= 80  # 20 + 50 + 10 = 80
        assert status == HealthStatus.CRITICAL
        assert len(issues) >= 2

    @pytest.mark.asyncio
    async def test_calculate_health_score_capped_at_100(self, service, mock_session):
        """Score is capped at 100."""
        tx = self._mock_transaction(
            closing_date=date.today() + timedelta(days=1)  # +30 points
        )

        tx_result = MagicMock()
        tx_result.scalar_one_or_none.return_value = tx

        # 5 overdue deadlines = 125 points
        overdue_result = MagicMock()
        overdue_result.scalar.return_value = 5

        other_result = MagicMock()
        other_result.scalar.return_value = 0

        mock_session.execute.side_effect = [tx_result, overdue_result, other_result, other_result, other_result]

        score, status, issues = await service.calculate_health(tx.id)

        assert score == 100  # Capped

    @pytest.mark.asyncio
    async def test_update_transaction_health(self, service, mock_session):
        """Updates transaction with calculated health."""
        tx = self._mock_transaction(
            closing_date=date.today() + timedelta(days=30)
        )

        # First call for calculate_health (transaction query)
        tx_result = MagicMock()
        tx_result.scalar_one_or_none.return_value = tx

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        # Second call for update (transaction query again)
        tx_result2 = MagicMock()
        tx_result2.scalar_one_or_none.return_value = tx

        mock_session.execute.side_effect = [
            tx_result, count_result, count_result, count_result, count_result,
            tx_result2
        ]

        result = await service.update_transaction_health(tx.id)

        assert result == tx
        mock_session.flush.assert_called()


class TestPriorityServiceFactory:
    """Tests for service factory."""

    def test_get_priority_service(self):
        """Factory returns service instance."""
        mock_session = MagicMock()
        service = get_priority_service(mock_session)
        assert isinstance(service, PriorityService)
