"""Deadline management endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db import get_db

router = APIRouter()


# === Request/Response Models ===


class DeadlineResponse(BaseModel):
    """Deadline response model."""

    id: UUID
    transaction_id: UUID
    deadline_type: str
    name: str
    due_date: date
    status: str
    days_remaining: int | None
    notes: str | None


class CreateDeadlineRequest(BaseModel):
    """Request to create a custom deadline."""

    transaction_id: UUID
    name: str
    due_date: date
    deadline_type: str = "custom"
    notes: str | None = None


class UpdateDeadlineRequest(BaseModel):
    """Request to update a deadline."""

    due_date: date | None = None
    status: str | None = None
    notes: str | None = None


# === Endpoints ===


@router.get("/transaction/{transaction_id}")
async def list_transaction_deadlines(
    transaction_id: UUID,
    include_completed: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[DeadlineResponse]:
    """
    List all deadlines for a transaction.

    Returns deadlines sorted by due date with status and
    days remaining calculated.
    """
    # TODO: Implement deadline listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Deadline listing not yet implemented",
    )


@router.get("/upcoming")
async def list_upcoming_deadlines(
    days_ahead: int = 7,
    db: AsyncSession = Depends(get_db),
) -> list[DeadlineResponse]:
    """
    List all upcoming deadlines across transactions.

    Useful for dashboard view of what needs attention.
    """
    # TODO: Implement upcoming deadlines
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Upcoming deadlines not yet implemented",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_deadline(
    request: CreateDeadlineRequest,
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """
    Create a custom deadline.

    Most deadlines are auto-generated from contract extraction,
    but users can add custom deadlines for items not in the contract.
    """
    # TODO: Implement deadline creation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Deadline creation not yet implemented",
    )


@router.patch("/{deadline_id}")
async def update_deadline(
    deadline_id: UUID,
    request: UpdateDeadlineRequest,
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """
    Update a deadline.

    Allows extending dates, adding notes, or marking status.
    Extensions are logged in audit trail.
    """
    # TODO: Implement deadline updates
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Deadline update not yet implemented",
    )


@router.post("/{deadline_id}/complete")
async def complete_deadline(
    deadline_id: UUID,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """
    Mark a deadline as completed.

    Records completion time and user, updates transaction checklist.
    """
    # TODO: Implement deadline completion
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Deadline completion not yet implemented",
    )


@router.post("/{deadline_id}/waive")
async def waive_deadline(
    deadline_id: UUID,
    reason: str,
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """
    Waive a deadline (e.g., inspection waived by buyer).

    Requires a reason for audit trail purposes.
    """
    # TODO: Implement deadline waiver
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Deadline waiver not yet implemented",
    )


@router.delete("/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deadline(
    deadline_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a custom deadline.

    Only custom deadlines can be deleted; contract-derived
    deadlines must be waived instead.
    """
    # TODO: Implement deadline deletion
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Deadline deletion not yet implemented",
    )
