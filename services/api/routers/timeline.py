"""Unified timeline and composite endpoints for transactions."""

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm.attributes import flag_modified

from services.api.dependencies import (
    CurrentUserDep,
    TransactionServiceDep,
    DeadlineServiceDep,
    DocumentServiceDep,
    DbSessionDep,
)
from packages.core.services.communication_log import get_communication_log_service
from packages.core.services.priority import get_priority_service

router = APIRouter()


# === Response Models ===


class TimelineEvent(BaseModel):
    """A single event in the transaction timeline."""

    id: str
    event_type: str  # document, deadline, communication, status_change, checklist
    title: str
    description: str | None = None
    timestamp: datetime
    actor: str | None = None  # Who performed the action
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None  # completed, pending, overdue, etc.
    icon: str | None = None  # Suggested icon for frontend


class TimelineResponse(BaseModel):
    """Timeline of all transaction events."""

    transaction_id: UUID
    events: list[TimelineEvent]
    total: int
    has_more: bool


class HealthScore(BaseModel):
    """Transaction health score details."""

    score: int
    status: str  # on_track, attention, critical
    issues: list[str]


class PartyInfo(BaseModel):
    """Party information for composite response."""

    role: str
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None


class DeadlineSummary(BaseModel):
    """Deadline summary for composite response."""

    id: UUID
    name: str
    due_date: date
    status: str
    days_remaining: int
    category: str | None = None


class DocumentSummary(BaseModel):
    """Document summary for composite response."""

    id: UUID
    filename: str
    document_type: str
    status: str
    uploaded_at: datetime
    needs_review: bool


class ChecklistItemResponse(BaseModel):
    """Checklist item with update capability."""

    id: str
    name: str
    description: str | None = None
    category: str
    required: bool
    status: str  # not_started, in_progress, completed, blocked
    document_id: str | None = None
    completed_at: datetime | None = None
    completed_by: str | None = None


class CommunicationSummary(BaseModel):
    """Recent communication summary."""

    id: UUID
    direction: str
    channel: str
    subject: str | None
    preview: str
    topic: str | None
    timestamp: datetime
    from_party: str | None = None
    to_party: str | None = None


class CompositeTransactionResponse(BaseModel):
    """
    Complete transaction data in a single response.

    Combines transaction details, parties, deadlines, documents,
    checklist, communications, and health score.
    """

    # Basic info
    id: UUID
    status: str
    transaction_type: str
    property_address: dict[str, Any]
    purchase_price: float | None
    year_built: int | None
    effective_date: date | None
    closing_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Health
    health: HealthScore

    # Related data
    parties: list[PartyInfo]
    deadlines: list[DeadlineSummary]
    documents: list[DocumentSummary]
    checklist: list[ChecklistItemResponse]
    recent_communications: list[CommunicationSummary]

    # Summary stats
    stats: dict[str, Any]


class UpdateChecklistItemRequest(BaseModel):
    """Request to update a checklist item."""

    status: str = Field(..., pattern="^(not_started|in_progress|completed|blocked)$")
    notes: str | None = None


class ChecklistUpdateResponse(BaseModel):
    """Response after updating checklist item."""

    item: ChecklistItemResponse
    checklist_completion: float
    message: str


# === Endpoints ===


@router.get("/{transaction_id}/full", response_model=CompositeTransactionResponse)
async def get_full_transaction(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    tx_service: TransactionServiceDep,
    deadline_service: DeadlineServiceDep,
    doc_service: DocumentServiceDep,
    db: DbSessionDep,
) -> CompositeTransactionResponse:
    """
    Get complete transaction data in a single API call.

    Returns all transaction-related data including:
    - Transaction details and parties
    - Health score and issues
    - All deadlines with status
    - All documents with extraction status
    - Complete checklist with progress
    - Recent communications

    This endpoint consolidates what would otherwise require 3+ separate API calls.
    """
    # Get transaction
    transaction = await tx_service.get_transaction(
        transaction_id, current_user.organization_id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Get health score
    priority_service = get_priority_service(db)
    score, health_status, issues = await priority_service.calculate_health(transaction_id)

    # Get deadlines
    deadlines = await deadline_service.get_transaction_deadlines(
        transaction_id,
        current_user.organization_id,
        include_completed=True,
    )

    # Get documents
    documents = await doc_service.get_transaction_documents(
        transaction_id,
        current_user.organization_id,
    )

    # Get communications
    comm_service = get_communication_log_service(db)
    communications = await comm_service.get_transaction_communications(
        transaction_id,
        limit=10,
    )

    # Build checklist response
    checklist_items = []
    checklist_completion = 0.0
    if transaction.checklist:
        items = transaction.checklist.items or []
        completed = sum(1 for i in items if i.get("status") == "completed")
        checklist_completion = (completed / len(items) * 100) if items else 0.0
        checklist_items = [
            ChecklistItemResponse(
                id=i.get("id", ""),
                name=i.get("name", ""),
                description=i.get("description"),
                category=i.get("category", ""),
                required=i.get("required", True),
                status=i.get("status", "not_started"),
                document_id=i.get("document_id"),
                completed_at=i.get("completed_at"),
                completed_by=i.get("completed_by"),
            )
            for i in items
        ]

    # Build parties list
    parties = [
        PartyInfo(
            role=p.get("role", ""),
            name=p.get("name", ""),
            email=p.get("email"),
            phone=p.get("phone"),
            company=p.get("company"),
        )
        for p in (transaction.parties or [])
    ]

    # Build deadline summaries
    today = date.today()
    deadline_summaries = [
        DeadlineSummary(
            id=d.id,
            name=d.name,
            due_date=d.due_date,
            status=d.status,
            days_remaining=(d.due_date - today).days,
            category=d.category,
        )
        for d in deadlines
    ]

    # Build document summaries
    document_summaries = [
        DocumentSummary(
            id=d.id,
            filename=d.filename,
            document_type=d.document_type,
            status=d.status,
            uploaded_at=d.uploaded_at,
            needs_review=d.status == "needs_review",
        )
        for d in documents
    ]

    # Build communication summaries
    comm_summaries = [
        CommunicationSummary(
            id=c.id,
            direction=c.direction,
            channel=c.channel,
            subject=c.subject,
            preview=c.body_preview or "",
            topic=c.topic,
            timestamp=c.timestamp,
            from_party=c.from_party,
            to_party=c.to_party,
        )
        for c in communications
    ]

    # Calculate stats
    overdue_deadlines = sum(1 for d in deadline_summaries if d.days_remaining < 0)
    pending_documents = sum(1 for d in document_summaries if d.status in ["uploaded", "processing"])
    review_documents = sum(1 for d in document_summaries if d.needs_review)

    stats = {
        "total_deadlines": len(deadlines),
        "overdue_deadlines": overdue_deadlines,
        "upcoming_deadlines": sum(1 for d in deadline_summaries if 0 <= d.days_remaining <= 7),
        "total_documents": len(documents),
        "pending_documents": pending_documents,
        "review_documents": review_documents,
        "checklist_completion": round(checklist_completion, 1),
        "days_to_closing": (transaction.closing_date - today).days if transaction.closing_date else None,
    }

    return CompositeTransactionResponse(
        id=transaction.id,
        status=transaction.status,
        transaction_type=transaction.transaction_type,
        property_address=transaction.property_address,
        purchase_price=float(transaction.purchase_price) if transaction.purchase_price else None,
        year_built=transaction.year_built,
        effective_date=transaction.effective_date,
        closing_date=transaction.closing_date,
        notes=transaction.notes,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        health=HealthScore(
            score=score,
            status=health_status,
            issues=issues,
        ),
        parties=parties,
        deadlines=deadline_summaries,
        documents=document_summaries,
        checklist=checklist_items,
        recent_communications=comm_summaries,
        stats=stats,
    )


@router.get("/{transaction_id}/timeline", response_model=TimelineResponse)
async def get_transaction_timeline(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    tx_service: TransactionServiceDep,
    deadline_service: DeadlineServiceDep,
    doc_service: DocumentServiceDep,
    db: DbSessionDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event_types: str | None = Query(None, description="Comma-separated event types to filter"),
) -> TimelineResponse:
    """
    Get unified timeline of all transaction events.

    Combines documents, deadlines, communications, status changes,
    and checklist updates into a single chronological timeline.

    Event types: document, deadline, communication, status_change, checklist
    """
    # Verify transaction access
    transaction = await tx_service.get_transaction(
        transaction_id, current_user.organization_id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    events: list[TimelineEvent] = []

    # Filter by event types if specified
    filter_types = set(event_types.split(",")) if event_types else None

    # Add document events
    if not filter_types or "document" in filter_types:
        documents = await doc_service.get_transaction_documents(
            transaction_id, current_user.organization_id
        )
        for doc in documents:
            events.append(TimelineEvent(
                id=f"doc-{doc.id}",
                event_type="document",
                title=f"Document uploaded: {doc.filename}",
                description=f"Type: {doc.document_type}, Status: {doc.status}",
                timestamp=doc.uploaded_at,
                metadata={
                    "document_id": str(doc.id),
                    "document_type": doc.document_type,
                    "filename": doc.filename,
                    "status": doc.status,
                },
                status="completed" if doc.status == "verified" else "pending",
                icon="document",
            ))

    # Add deadline events
    if not filter_types or "deadline" in filter_types:
        deadlines = await deadline_service.get_transaction_deadlines(
            transaction_id, current_user.organization_id, include_completed=True
        )
        today = date.today()
        for dl in deadlines:
            days_remaining = (dl.due_date - today).days
            if days_remaining < 0:
                dl_status = "overdue"
            elif dl.status == "completed":
                dl_status = "completed"
            elif days_remaining <= 3:
                dl_status = "urgent"
            else:
                dl_status = "pending"

            events.append(TimelineEvent(
                id=f"deadline-{dl.id}",
                event_type="deadline",
                title=f"Deadline: {dl.name}",
                description=f"Due: {dl.due_date.strftime('%B %d, %Y')}",
                timestamp=datetime.combine(dl.due_date, datetime.min.time()),
                metadata={
                    "deadline_id": str(dl.id),
                    "due_date": str(dl.due_date),
                    "days_remaining": days_remaining,
                    "category": dl.category,
                },
                status=dl_status,
                icon="calendar",
            ))

    # Add communication events
    if not filter_types or "communication" in filter_types:
        comm_service = get_communication_log_service(db)
        communications = await comm_service.get_transaction_communications(
            transaction_id, limit=100
        )
        for comm in communications:
            direction_text = "Received" if comm.direction == "inbound" else "Sent"
            events.append(TimelineEvent(
                id=f"comm-{comm.id}",
                event_type="communication",
                title=f"{direction_text}: {comm.subject or 'No subject'}",
                description=comm.body_preview,
                timestamp=comm.timestamp,
                actor=comm.from_party,
                metadata={
                    "communication_id": str(comm.id),
                    "direction": comm.direction,
                    "channel": comm.channel,
                    "topic": comm.topic,
                    "from": comm.from_party,
                    "to": comm.to_party,
                },
                status="completed",
                icon="email" if comm.channel == "email" else "phone",
            ))

    # Add checklist events
    if not filter_types or "checklist" in filter_types:
        if transaction.checklist:
            for item in (transaction.checklist.items or []):
                completed_at = item.get("completed_at")
                if completed_at:
                    # Handle both string and datetime values
                    if isinstance(completed_at, str):
                        completed_at = datetime.fromisoformat(completed_at)
                    events.append(TimelineEvent(
                        id=f"checklist-{item.get('id')}",
                        event_type="checklist",
                        title=f"Completed: {item.get('name')}",
                        description=item.get("description"),
                        timestamp=completed_at,
                        actor=item.get("completed_by"),
                        metadata={
                            "item_id": item.get("id"),
                            "category": item.get("category"),
                        },
                        status="completed",
                        icon="check",
                    ))

    # Sort by timestamp descending (most recent first)
    events.sort(key=lambda e: e.timestamp, reverse=True)

    # Apply pagination
    total = len(events)
    events = events[offset:offset + limit]

    return TimelineResponse(
        transaction_id=transaction_id,
        events=events,
        total=total,
        has_more=offset + limit < total,
    )


@router.patch(
    "/{transaction_id}/checklist/{item_id}",
    response_model=ChecklistUpdateResponse,
)
async def update_checklist_item(
    transaction_id: UUID,
    item_id: str,
    request: UpdateChecklistItemRequest,
    current_user: CurrentUserDep,
    tx_service: TransactionServiceDep,
    db: DbSessionDep,
) -> ChecklistUpdateResponse:
    """
    Update a checklist item status.

    Allows manually marking checklist items as completed, in progress, or blocked.
    This is useful for items that can't be automatically tracked.

    Status values:
    - not_started: Item hasn't been worked on
    - in_progress: Work has begun but isn't complete
    - completed: Item is done
    - blocked: Item is blocked by external dependency
    """
    transaction = await tx_service.get_transaction(
        transaction_id, current_user.organization_id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    if not transaction.checklist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction has no checklist",
        )

    # Find and update the item
    items = transaction.checklist.items or []
    found = False
    updated_item = None

    for item in items:
        if item.get("id") == item_id:
            found = True
            item["status"] = request.status
            if request.status == "completed":
                item["completed_at"] = datetime.now(timezone.utc).isoformat()
                item["completed_by"] = str(current_user.id)
            elif request.status == "not_started":
                item["completed_at"] = None
                item["completed_by"] = None

            if request.notes:
                item["notes"] = request.notes

            updated_item = ChecklistItemResponse(
                id=item.get("id", ""),
                name=item.get("name", ""),
                description=item.get("description"),
                category=item.get("category", ""),
                required=item.get("required", True),
                status=item.get("status", "not_started"),
                document_id=item.get("document_id"),
                completed_at=item.get("completed_at"),
                completed_by=item.get("completed_by"),
            )
            break

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist item '{item_id}' not found",
        )

    # Update the checklist - mark JSONB column as modified for SQLAlchemy
    transaction.checklist.items = items
    flag_modified(transaction.checklist, "items")
    await db.flush()

    # Calculate completion
    completed = sum(1 for i in items if i.get("status") == "completed")
    completion = (completed / len(items) * 100) if items else 0.0

    return ChecklistUpdateResponse(
        item=updated_item,
        checklist_completion=round(completion, 1),
        message=f"Checklist item updated to '{request.status}'",
    )
