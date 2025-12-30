"""Unit tests for timeline and composite endpoints."""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4

from services.api.routers.timeline import (
    TimelineEvent,
    TimelineResponse,
    HealthScore,
    PartyInfo,
    DeadlineSummary,
    DocumentSummary,
    ChecklistItemResponse,
    CommunicationSummary,
    CompositeTransactionResponse,
    UpdateChecklistItemRequest,
    ChecklistUpdateResponse,
)


class TestTimelineModels:
    """Tests for timeline data models."""

    def test_timeline_event_creation(self):
        """Creates a timeline event."""
        event = TimelineEvent(
            id="doc-123",
            event_type="document",
            title="Document uploaded",
            description="Contract uploaded",
            timestamp=datetime.now(),
            status="completed",
            icon="document",
        )

        assert event.id == "doc-123"
        assert event.event_type == "document"
        assert event.title == "Document uploaded"

    def test_timeline_event_with_metadata(self):
        """Timeline event with metadata."""
        event = TimelineEvent(
            id="deadline-456",
            event_type="deadline",
            title="Deadline approaching",
            timestamp=datetime.now(),
            metadata={
                "deadline_id": str(uuid4()),
                "days_remaining": 3,
            },
        )

        assert "deadline_id" in event.metadata
        assert event.metadata["days_remaining"] == 3

    def test_timeline_response(self):
        """Creates a timeline response."""
        events = [
            TimelineEvent(
                id=f"event-{i}",
                event_type="document",
                title=f"Event {i}",
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        response = TimelineResponse(
            transaction_id=uuid4(),
            events=events,
            total=10,
            has_more=True,
        )

        assert len(response.events) == 5
        assert response.total == 10
        assert response.has_more is True


class TestHealthScoreModel:
    """Tests for health score model."""

    def test_health_score_on_track(self):
        """Health score for on-track transaction."""
        health = HealthScore(
            score=20,
            status="on_track",
            issues=[],
        )

        assert health.score == 20
        assert health.status == "on_track"
        assert len(health.issues) == 0

    def test_health_score_critical(self):
        """Health score for critical transaction."""
        health = HealthScore(
            score=85,
            status="critical",
            issues=[
                "3 overdue deadlines",
                "Closing in 2 days",
            ],
        )

        assert health.score == 85
        assert health.status == "critical"
        assert len(health.issues) == 2


class TestPartyInfo:
    """Tests for party info model."""

    def test_party_info_basic(self):
        """Basic party info."""
        party = PartyInfo(
            role="buyer",
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
        )

        assert party.role == "buyer"
        assert party.name == "John Doe"
        assert party.email == "john@example.com"

    def test_party_info_with_company(self):
        """Party info with company."""
        party = PartyInfo(
            role="title_company",
            name="Jane Smith",
            email="jane@titleco.com",
            company="ABC Title Company",
        )

        assert party.company == "ABC Title Company"


class TestDeadlineSummary:
    """Tests for deadline summary model."""

    def test_deadline_summary(self):
        """Creates deadline summary."""
        deadline = DeadlineSummary(
            id=uuid4(),
            name="Inspection Period",
            due_date=date.today() + timedelta(days=5),
            status="pending",
            days_remaining=5,
            category="contingency",
        )

        assert deadline.name == "Inspection Period"
        assert deadline.days_remaining == 5
        assert deadline.category == "contingency"

    def test_deadline_overdue(self):
        """Deadline that is overdue."""
        deadline = DeadlineSummary(
            id=uuid4(),
            name="Earnest Money Due",
            due_date=date.today() - timedelta(days=2),
            status="overdue",
            days_remaining=-2,
        )

        assert deadline.days_remaining < 0
        assert deadline.status == "overdue"


class TestChecklistItemResponse:
    """Tests for checklist item response model."""

    def test_checklist_item_not_started(self):
        """Checklist item not started."""
        item = ChecklistItemResponse(
            id="earnest_money_1",
            name="Earnest Money Deposit",
            description="Collect and deposit earnest money",
            category="financial",
            required=True,
            status="not_started",
        )

        assert item.status == "not_started"
        assert item.required is True
        assert item.completed_at is None

    def test_checklist_item_completed(self):
        """Checklist item completed."""
        item = ChecklistItemResponse(
            id="inspection_1",
            name="Home Inspection",
            category="contingency",
            required=True,
            status="completed",
            completed_at=datetime.now(),
            completed_by="user-123",
        )

        assert item.status == "completed"
        assert item.completed_at is not None
        assert item.completed_by == "user-123"


class TestUpdateChecklistItemRequest:
    """Tests for update checklist item request."""

    def test_valid_status_values(self):
        """Accepts valid status values."""
        for status in ["not_started", "in_progress", "completed", "blocked"]:
            request = UpdateChecklistItemRequest(status=status)
            assert request.status == status

    def test_with_notes(self):
        """Request with notes."""
        request = UpdateChecklistItemRequest(
            status="completed",
            notes="Completed by agent on 2024-01-15",
        )

        assert request.notes is not None


class TestCompositeTransactionResponse:
    """Tests for composite transaction response."""

    def test_composite_response_structure(self):
        """Validates composite response structure."""
        response = CompositeTransactionResponse(
            id=uuid4(),
            status="active",
            transaction_type="purchase",
            property_address={"street": "123 Main St", "city": "Miami"},
            purchase_price=350000.0,
            year_built=2005,
            effective_date=date.today(),
            closing_date=date.today() + timedelta(days=30),
            notes=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            health=HealthScore(score=25, status="on_track", issues=[]),
            parties=[],
            deadlines=[],
            documents=[],
            checklist=[],
            recent_communications=[],
            stats={
                "total_deadlines": 5,
                "overdue_deadlines": 0,
                "checklist_completion": 40.0,
            },
        )

        assert response.status == "active"
        assert response.purchase_price == 350000.0
        assert response.health.status == "on_track"
        assert response.stats["checklist_completion"] == 40.0
