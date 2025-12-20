"""Transaction management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db import get_db

router = APIRouter()


# === Request/Response Models ===


class CreateTransactionRequest(BaseModel):
    """Request to create a new transaction."""

    transaction_type: str  # purchase, sale, dual
    property_address: dict[str, str]
    purchase_price: float | None = None


class TransactionResponse(BaseModel):
    """Transaction response model."""

    id: UUID
    status: str
    transaction_type: str
    property_address: dict[str, str]
    purchase_price: float | None
    effective_date: str | None
    closing_date: str | None


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""

    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


# === Endpoints ===


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    request: CreateTransactionRequest,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """
    Create a new transaction.

    This creates a transaction shell that can then have documents uploaded,
    deadlines tracked, and checklists generated.
    """
    # TODO: Implement transaction creation
    # 1. Validate organization context from auth
    # 2. Create transaction record
    # 3. Initialize FL checklist template
    # 4. Return created transaction
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction creation not yet implemented",
    )


@router.get("/")
async def list_transactions(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """
    List transactions for the current organization.

    Supports pagination and filtering by status.
    """
    # TODO: Implement transaction listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction listing not yet implemented",
    )


@router.get("/{transaction_id}")
async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """
    Get a specific transaction by ID.

    Returns full transaction details including parties, documents,
    deadlines, and checklist status.
    """
    # TODO: Implement transaction retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction retrieval not yet implemented",
    )


@router.patch("/{transaction_id}")
async def update_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """
    Update transaction details.

    Allows updating status, parties, dates, and notes.
    """
    # TODO: Implement transaction updates
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction update not yet implemented",
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a transaction.

    Only allowed for draft transactions. Active transactions
    should be cancelled instead.
    """
    # TODO: Implement transaction deletion
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction deletion not yet implemented",
    )
