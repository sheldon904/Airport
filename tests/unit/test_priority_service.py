"""Unit tests for priority/health scoring service."""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from packages.core.services.priority import (
    PriorityService,
    HealthStatus,
    get_priority_service,
)


class TestHealthStatusConstants:
    """Tests for health status constants."""

    def test_health_statuses_defined(self):
        """Health statuses are defined."""
        assert HealthStatus.ON_TRACK == "on_track"
        assert HealthStatus.NEEDS_ATTENTION == "needs_attention"
        assert HealthStatus.AT_RISK == "at_risk"
        assert HealthStatus.CRITICAL == "critical"


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

    def test_calculate_deadline_score(self, service):
        """Calculates deadline compliance score."""
        deadlines = [
            {"status": "completed"},
            {"status": "completed"},
            {"status": "pending"},
            {"status": "overdue"},
        ]

        score = service._calculate_deadline_score(deadlines)
        # 2 completed out of 4 = 50%
        assert score == 50

    def test_calculate_deadline_score_all_complete(self, service):
        """Perfect score for all completed deadlines."""
        deadlines = [
            {"status": "completed"},
            {"status": "completed"},
            {"status": "completed"},
        ]

        score = service._calculate_deadline_score(deadlines)
        assert score == 100

    def test_calculate_deadline_score_empty(self, service):
        """Empty deadlines return 100 (no deadlines to miss)."""
        score = service._calculate_deadline_score([])
        assert score == 100

    def test_calculate_document_score(self, service):
        """Calculates document completion score."""
        documents = [
            {"status": "verified"},
            {"status": "extracted"},
            {"status": "pending"},
            {"status": "needs_review"},
        ]

        score = service._calculate_document_score(documents)
        # 2 complete (verified, extracted) out of 4 = 50%
        assert score == 50

    def test_calculate_document_score_all_verified(self, service):
        """Perfect score for all verified documents."""
        documents = [
            {"status": "verified"},
            {"status": "verified"},
        ]

        score = service._calculate_document_score(documents)
        assert score == 100

    def test_calculate_closing_proximity_score_far(self, service):
        """Far closing date gives high score."""
        future_date = date.today() + timedelta(days=60)
        score = service._calculate_closing_proximity_score(future_date)
        assert score >= 90

    def test_calculate_closing_proximity_score_near(self, service):
        """Near closing date gives lower score."""
        near_date = date.today() + timedelta(days=7)
        score = service._calculate_closing_proximity_score(near_date)
        assert score < 90

    def test_calculate_closing_proximity_score_past(self, service):
        """Past closing date gives low score."""
        past_date = date.today() - timedelta(days=1)
        score = service._calculate_closing_proximity_score(past_date)
        assert score < 50

    def test_calculate_closing_proximity_score_none(self, service):
        """No closing date returns neutral score."""
        score = service._calculate_closing_proximity_score(None)
        assert score == 70

    def test_determine_health_status_on_track(self, service):
        """High score indicates on track."""
        status, issues = service._determine_health_status(
            priority_score=85,
            overdue_count=0,
            pending_review_count=0,
            days_to_closing=30,
        )
        assert status == HealthStatus.ON_TRACK
        assert len(issues) == 0

    def test_determine_health_status_needs_attention(self, service):
        """Medium score indicates needs attention."""
        status, issues = service._determine_health_status(
            priority_score=65,
            overdue_count=1,
            pending_review_count=2,
            days_to_closing=20,
        )
        assert status == HealthStatus.NEEDS_ATTENTION
        assert len(issues) > 0

    def test_determine_health_status_at_risk(self, service):
        """Low score indicates at risk."""
        status, issues = service._determine_health_status(
            priority_score=45,
            overdue_count=3,
            pending_review_count=5,
            days_to_closing=10,
        )
        assert status == HealthStatus.AT_RISK
        assert "overdue" in " ".join(issues).lower()

    def test_determine_health_status_critical(self, service):
        """Very low score indicates critical."""
        status, issues = service._determine_health_status(
            priority_score=25,
            overdue_count=5,
            pending_review_count=10,
            days_to_closing=3,
        )
        assert status == HealthStatus.CRITICAL

    def test_issues_reported_for_overdue(self, service):
        """Issues list includes overdue deadlines."""
        status, issues = service._determine_health_status(
            priority_score=60,
            overdue_count=2,
            pending_review_count=0,
            days_to_closing=15,
        )
        assert any("overdue" in i.lower() for i in issues)

    def test_issues_reported_for_pending_review(self, service):
        """Issues list includes documents needing review."""
        status, issues = service._determine_health_status(
            priority_score=60,
            overdue_count=0,
            pending_review_count=3,
            days_to_closing=15,
        )
        assert any("review" in i.lower() or "document" in i.lower() for i in issues)

    def test_issues_reported_for_near_closing(self, service):
        """Issues list includes near closing warning."""
        status, issues = service._determine_health_status(
            priority_score=70,
            overdue_count=0,
            pending_review_count=0,
            days_to_closing=5,
        )
        assert any("close" in i.lower() or "closing" in i.lower() for i in issues)


class TestPriorityServiceFactory:
    """Tests for service factory."""

    def test_get_priority_service(self):
        """Factory returns service instance."""
        mock_session = MagicMock()
        service = get_priority_service(mock_session)
        assert isinstance(service, PriorityService)
