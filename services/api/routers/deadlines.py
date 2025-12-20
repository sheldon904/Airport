"""Deadline management endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from services.api.dependencies import CurrentUserDep, DeadlineServiceDep

router = APIRouter()


# === Request/Response Models ===


class DeadlineResponse(BaseModel):
    """Deadline response model."""

    id: UUID
    transaction_id: UUID
    deadline_type: str
    name: str
    title: str  # Alias for name for frontend compatibility
    description: str | None
    due_date: date
    status: str
    days_remaining: int
    notes: str | None
    completed_at: str | None
    source_document_id: UUID | None
    is_statutory: bool  # Whether deadline is mandated by FL statute
    statutory_reference: str | None  # FL statute reference if applicable


class CreateDeadlineRequest(BaseModel):
    """Request to create a custom deadline."""

    transaction_id: UUID
    name: str
    due_date: date
    deadline_type: str = "custom"
    description: str | None = None


class UpdateDeadlineRequest(BaseModel):
    """Request to update a deadline."""

    due_date: date | None = None
    name: str | None = None
    notes: str | None = None


class CompleteDeadlineRequest(BaseModel):
    """Request to complete a deadline."""

    notes: str | None = None


class WaiveDeadlineRequest(BaseModel):
    """Request to waive a deadline."""

    reason: str


class ExtendDeadlineRequest(BaseModel):
    """Request to extend a deadline."""

    new_date: date
    reason: str | None = None


class UpcomingDeadlineResponse(BaseModel):
    """Upcoming deadline with transaction context."""

    id: str
    name: str
    title: str  # Alias for name for frontend compatibility
    due_date: str
    days_remaining: int
    status: str
    deadline_type: str
    transaction_id: str
    property_address: str
    is_statutory: bool  # Whether deadline is mandated by FL statute


# === Helper Functions ===


# Florida statutory deadlines and their references
FL_STATUTORY_DEADLINES = {
    "inspection_period": ("F.S. 475.278", True),
    "financing_contingency": ("F.S. 475.25", True),
    "title_review": ("F.S. 689.01", True),
    "hoa_disclosure_review": ("F.S. 720.401", True),
    "lead_paint_disclosure": ("42 U.S.C. 4852d", True),  # Federal
    "right_to_cancel": ("F.S. 501.025", True),
    "closing": (None, False),
    "earnest_money": (None, False),
    "appraisal": (None, False),
    "custom": (None, False),
}


def get_statutory_info(deadline_type: str) -> tuple[str | None, bool]:
    """Get statutory reference and is_statutory flag for a deadline type."""
    return FL_STATUTORY_DEADLINES.get(deadline_type, (None, False))


def deadline_to_response(deadline) -> DeadlineResponse:
    """Convert deadline model to response."""
    days_remaining = (deadline.due_date - date.today()).days
    statutory_ref, is_statutory = get_statutory_info(deadline.deadline_type)

    return DeadlineResponse(
        id=deadline.id,
        transaction_id=deadline.transaction_id,
        deadline_type=deadline.deadline_type,
        name=deadline.name,
        title=deadline.name,  # Alias for frontend compatibility
        description=deadline.description,
        due_date=deadline.due_date,
        status=deadline.status,
        days_remaining=days_remaining,
        notes=deadline.notes,
        completed_at=deadline.completed_at.isoformat() if deadline.completed_at else None,
        source_document_id=deadline.source_document_id,
        is_statutory=is_statutory,
        statutory_reference=statutory_ref,
    )


# === Endpoints ===


@router.get("/transaction/{transaction_id}", response_model=list[DeadlineResponse])
async def list_transaction_deadlines(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
    include_completed: bool = Query(False),
) -> list[DeadlineResponse]:
    """
    List all deadlines for a transaction.

    Returns deadlines sorted by due date with status and
    days remaining calculated.
    """
    deadlines = await service.get_transaction_deadlines(
        transaction_id,
        current_user.organization_id,
        include_completed=include_completed,
    )

    return [deadline_to_response(d) for d in deadlines]


@router.get("/upcoming", response_model=list[UpcomingDeadlineResponse])
async def list_upcoming_deadlines(
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
    days_ahead: int = Query(7, ge=1, le=90),
) -> list[UpcomingDeadlineResponse]:
    """
    List all upcoming deadlines across transactions.

    Useful for dashboard view of what needs attention.
    """
    deadlines = await service.get_upcoming_deadlines(
        current_user.organization_id,
        days_ahead=days_ahead,
    )

    return [UpcomingDeadlineResponse(**d) for d in deadlines]


@router.get("/overdue", response_model=list[DeadlineResponse])
async def list_overdue_deadlines(
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
) -> list[DeadlineResponse]:
    """Get all overdue deadlines across transactions."""
    deadlines = await service.get_overdue_deadlines(current_user.organization_id)
    return [deadline_to_response(d) for d in deadlines]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=DeadlineResponse)
async def create_deadline(
    request: CreateDeadlineRequest,
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
) -> DeadlineResponse:
    """
    Create a custom deadline.

    Most deadlines are auto-generated from contract extraction,
    but users can add custom deadlines for items not in the contract.
    """
    try:
        deadline = await service.create_deadline(
            transaction_id=request.transaction_id,
            organization_id=current_user.organization_id,
            deadline_type=request.deadline_type,
            name=request.name,
            due_date=request.due_date,
            description=request.description,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return deadline_to_response(deadline)


@router.patch("/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(
    deadline_id: UUID,
    request: UpdateDeadlineRequest,
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
) -> DeadlineResponse:
    """
    Update a deadline.

    Allows updating due date, name, and notes.
    """
    deadline = await service.update_deadline(
        deadline_id,
        current_user.organization_id,
        due_date=request.due_date,
        name=request.name,
        notes=request.notes,
    )

    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )

    return deadline_to_response(deadline)


@router.post("/{deadline_id}/complete", response_model=DeadlineResponse)
async def complete_deadline(
    deadline_id: UUID,
    request: CompleteDeadlineRequest,
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
) -> DeadlineResponse:
    """
    Mark a deadline as completed.

    Records completion time and user, updates transaction checklist.
    """
    deadline = await service.complete_deadline(
        deadline_id,
        current_user.organization_id,
        completed_by=current_user.id,
        notes=request.notes,
    )

    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )

    return deadline_to_response(deadline)


@router.post("/{deadline_id}/waive", response_model=DeadlineResponse)
async def waive_deadline(
    deadline_id: UUID,
    request: WaiveDeadlineRequest,
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
) -> DeadlineResponse:
    """
    Waive a deadline (e.g., inspection waived by buyer).

    Requires a reason for audit trail purposes.
    """
    try:
        deadline = await service.waive_deadline(
            deadline_id,
            current_user.organization_id,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )

    return deadline_to_response(deadline)


@router.post("/{deadline_id}/extend", response_model=DeadlineResponse)
async def extend_deadline(
    deadline_id: UUID,
    request: ExtendDeadlineRequest,
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
) -> DeadlineResponse:
    """
    Extend a deadline to a new date.

    Records the extension in the deadline notes for audit purposes.
    """
    try:
        deadline = await service.extend_deadline(
            deadline_id,
            current_user.organization_id,
            new_date=request.new_date,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )

    return deadline_to_response(deadline)


@router.delete("/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deadline(
    deadline_id: UUID,
    current_user: CurrentUserDep,
    service: DeadlineServiceDep,
) -> None:
    """
    Delete a custom deadline.

    Only custom deadlines can be deleted; contract-derived
    deadlines must be waived instead.
    """
    try:
        deleted = await service.delete_deadline(
            deadline_id,
            current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )
