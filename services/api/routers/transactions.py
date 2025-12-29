"""Transaction management endpoints."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.api.dependencies import (
    CurrentUserDep,
    TransactionServiceDep,
    DeadlineServiceDep,
)

router = APIRouter()


# === Request/Response Models ===


class PropertyAddress(BaseModel):
    """Property address model."""

    street: str
    unit: str | None = None
    city: str
    state: str = "FL"
    zip_code: str
    county: str | None = None


class PartyInfo(BaseModel):
    """Party information model."""

    role: str  # buyer, seller, buyer_agent, seller_agent, lender, title_company
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    license_number: str | None = None


class CreateTransactionRequest(BaseModel):
    """Request to create a new transaction."""

    transaction_type: str = Field(..., pattern="^(purchase|sale|dual|lease)$")
    property_address: PropertyAddress
    purchase_price: Decimal | None = None
    year_built: int | None = Field(None, ge=1800, le=2100)
    closing_date: date | None = None
    buyer_name: str | None = None
    seller_name: str | None = None
    notes: str | None = None


class UpdateTransactionRequest(BaseModel):
    """Request to update a transaction."""

    status: str | None = None
    purchase_price: Decimal | None = None
    effective_date: date | None = None
    closing_date: date | None = None
    notes: str | None = None


class AddPartyRequest(BaseModel):
    """Request to add a party to transaction."""

    party: PartyInfo


class ChecklistItem(BaseModel):
    """Checklist item response."""

    id: str
    name: str
    description: str | None
    category: str
    required: bool
    status: str
    document_id: str | None


class TransactionResponse(BaseModel):
    """Transaction response model."""

    id: UUID
    status: str
    transaction_type: str
    property_address: dict[str, Any]
    purchase_price: float | None
    year_built: int | None
    effective_date: date | None
    closing_date: date | None
    parties: list[dict[str, Any]]
    buyer_name: str | None = None
    seller_name: str | None = None
    notes: str | None
    created_at: str
    updated_at: str


class TransactionDetailResponse(TransactionResponse):
    """Detailed transaction response with related data."""

    documents_count: int = 0
    deadlines_count: int = 0
    checklist_completion: float = 0.0
    checklist_items: list[ChecklistItem] = []
    upcoming_deadlines: list[dict[str, Any]] = []


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""

    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class DashboardResponse(BaseModel):
    """Dashboard summary response."""

    active_transactions: int
    pending_review: int
    closing_soon: int
    closed_this_month: int
    upcoming_closings: list[dict[str, Any]]


# === Helper Functions ===


def _extract_party_name(parties: list[dict[str, Any]], role: str) -> str | None:
    """Extract party name by role from parties list."""
    if not parties:
        return None
    for party in parties:
        if party.get("role") == role:
            return party.get("name")
    return None


def transaction_to_response(transaction) -> TransactionResponse:
    """Convert transaction model to response."""
    parties = transaction.parties or []
    return TransactionResponse(
        id=transaction.id,
        status=transaction.status,
        transaction_type=transaction.transaction_type,
        property_address=transaction.property_address,
        purchase_price=float(transaction.purchase_price) if transaction.purchase_price else None,
        year_built=transaction.year_built,
        effective_date=transaction.effective_date,
        closing_date=transaction.closing_date,
        parties=parties,
        buyer_name=_extract_party_name(parties, "buyer"),
        seller_name=_extract_party_name(parties, "seller"),
        notes=transaction.notes,
        created_at=transaction.created_at.isoformat(),
        updated_at=transaction.updated_at.isoformat(),
    )


# === Endpoints ===


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TransactionResponse)
async def create_transaction(
    request: CreateTransactionRequest,
    current_user: CurrentUserDep,
    service: TransactionServiceDep,
) -> TransactionResponse:
    """
    Create a new transaction.

    Creates a transaction shell with an initialized Florida compliance
    checklist. The transaction starts in 'draft' status.
    """
    # Build initial parties list from buyer_name/seller_name if provided
    initial_parties: list[dict[str, Any]] = []
    if request.buyer_name:
        initial_parties.append({"role": "buyer", "name": request.buyer_name})
    if request.seller_name:
        initial_parties.append({"role": "seller", "name": request.seller_name})

    transaction = await service.create_transaction(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        transaction_type=request.transaction_type,
        property_address=request.property_address.model_dump(),
        purchase_price=request.purchase_price,
        year_built=request.year_built,
        closing_date=request.closing_date,
        parties=initial_parties if initial_parties else None,
        notes=request.notes,
    )

    return transaction_to_response(transaction)


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    current_user: CurrentUserDep,
    service: TransactionServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> TransactionListResponse:
    """
    List transactions for the current organization.

    Supports pagination and filtering by status.
    """
    transactions, total = await service.list_transactions(
        organization_id=current_user.organization_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    return TransactionListResponse(
        items=[transaction_to_response(t) for t in transactions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: CurrentUserDep,
    service: TransactionServiceDep,
) -> DashboardResponse:
    """Get dashboard summary for current organization."""
    summary = await service.get_dashboard_summary(current_user.organization_id)
    return DashboardResponse(**summary)


@router.get("/{transaction_id}", response_model=TransactionDetailResponse)
async def get_transaction(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    service: TransactionServiceDep,
    deadline_service: DeadlineServiceDep,
) -> TransactionDetailResponse:
    """
    Get a specific transaction by ID.

    Returns full transaction details including parties, documents,
    deadlines, and checklist status.
    """
    transaction = await service.get_transaction(
        transaction_id,
        current_user.organization_id,
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Get upcoming deadlines
    deadlines = await deadline_service.get_transaction_deadlines(
        transaction_id,
        current_user.organization_id,
        include_completed=False,
    )

    # Calculate checklist completion
    checklist_items = []
    checklist_completion = 0.0
    if transaction.checklist:
        items = transaction.checklist.items or []
        completed = sum(1 for i in items if i.get("status") == "completed")
        checklist_completion = (completed / len(items) * 100) if items else 0.0
        checklist_items = [
            ChecklistItem(
                id=i.get("id", ""),
                name=i.get("name", ""),
                description=i.get("description"),
                category=i.get("category", ""),
                required=i.get("required", True),
                status=i.get("status", "not_started"),
                document_id=i.get("document_id"),
            )
            for i in items
        ]

    return TransactionDetailResponse(
        id=transaction.id,
        status=transaction.status,
        transaction_type=transaction.transaction_type,
        property_address=transaction.property_address,
        purchase_price=float(transaction.purchase_price) if transaction.purchase_price else None,
        year_built=transaction.year_built,
        effective_date=transaction.effective_date,
        closing_date=transaction.closing_date,
        parties=transaction.parties or [],
        notes=transaction.notes,
        created_at=transaction.created_at.isoformat(),
        updated_at=transaction.updated_at.isoformat(),
        documents_count=len(transaction.documents) if transaction.documents else 0,
        deadlines_count=len(deadlines),
        checklist_completion=checklist_completion,
        checklist_items=checklist_items,
        upcoming_deadlines=[
            {
                "id": str(d.id),
                "name": d.name,
                "due_date": str(d.due_date),
                "status": d.status,
                "days_remaining": (d.due_date - date.today()).days,
            }
            for d in deadlines[:5]
        ],
    )


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    request: UpdateTransactionRequest,
    current_user: CurrentUserDep,
    service: TransactionServiceDep,
) -> TransactionResponse:
    """
    Update transaction details.

    Allows updating status, purchase price, dates, and notes.
    """
    try:
        transaction = await service.update_transaction(
            transaction_id,
            current_user.organization_id,
            status=request.status,
            purchase_price=request.purchase_price,
            effective_date=request.effective_date,
            closing_date=request.closing_date,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return transaction_to_response(transaction)


@router.post("/{transaction_id}/parties", response_model=TransactionResponse)
async def add_party(
    transaction_id: UUID,
    request: AddPartyRequest,
    current_user: CurrentUserDep,
    service: TransactionServiceDep,
) -> TransactionResponse:
    """Add a party to the transaction."""
    transaction = await service.add_party(
        transaction_id,
        current_user.organization_id,
        request.party.model_dump(),
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return transaction_to_response(transaction)


@router.delete("/{transaction_id}/parties/{party_id}", response_model=TransactionResponse)
async def remove_party(
    transaction_id: UUID,
    party_id: str,
    current_user: CurrentUserDep,
    service: TransactionServiceDep,
) -> TransactionResponse:
    """Remove a party from the transaction."""
    transaction = await service.remove_party(
        transaction_id,
        current_user.organization_id,
        party_id,
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return transaction_to_response(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    service: TransactionServiceDep,
) -> None:
    """
    Delete a transaction.

    Only allowed for draft transactions. Active transactions
    should be cancelled instead.
    """
    try:
        deleted = await service.delete_transaction(
            transaction_id,
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
            detail="Transaction not found",
        )
