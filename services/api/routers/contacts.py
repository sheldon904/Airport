"""Contacts router - lightweight CRM endpoints."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.session import get_db
from packages.core.services import ContactsService, get_contacts_service, ContactType
# REM-003: Use standard CurrentUserDep for consistent auth handling
from services.api.dependencies import CurrentUserDep, DbSessionDep


router = APIRouter()


class ContactCreate(BaseModel):
    """Request to create a new contact."""

    full_name: str
    email: EmailStr | None = None
    phone: str | None = None
    contact_type: str = ContactType.OTHER
    company: str | None = None
    notes: str | None = None
    tags: list[str] = []


class ContactUpdate(BaseModel):
    """Request to update a contact."""

    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    contact_type: str | None = None
    company: str | None = None
    notes: str | None = None


class ContactResponse(BaseModel):
    """Response with contact data."""

    id: str
    full_name: str
    email: str | None
    phone: str | None
    contact_type: str
    company: str | None
    source: str
    transaction_count: int
    last_transaction_id: str | None
    last_transaction_date: str | None
    tags: list[str]
    notes: str | None
    created_at: str
    updated_at: str


class ContactListResponse(BaseModel):
    """Response with list of contacts."""

    contacts: list[ContactResponse]
    total: int
    limit: int
    offset: int


def _contact_to_response(contact) -> ContactResponse:
    """Convert contact model to response."""
    return ContactResponse(
        id=str(contact.id),
        full_name=contact.full_name,
        email=contact.email,
        phone=contact.phone,
        contact_type=contact.contact_type,
        company=contact.company,
        source=contact.source,
        transaction_count=contact.transaction_count or 0,
        last_transaction_id=str(contact.last_transaction_id) if contact.last_transaction_id else None,
        last_transaction_date=str(contact.last_transaction_date) if contact.last_transaction_date else None,
        tags=contact.tags or [],
        notes=contact.notes,
        created_at=contact.created_at.isoformat() if contact.created_at else "",
        updated_at=contact.updated_at.isoformat() if contact.updated_at else "",
    )


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
    query: str | None = Query(None, description="Search query"),
    contact_type: str | None = Query(None, description="Filter by contact type"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> ContactListResponse:
    """
    List contacts with optional search and filtering.

    Search matches against name, email, phone, and company.
    """
    contacts_service = get_contacts_service(db)

    contacts, total = await contacts_service.search_contacts(
        current_user.organization_id,  # REM-003: Access as attribute
        query=query,
        contact_type=contact_type,
        limit=limit,
        offset=offset,
    )

    return ContactListResponse(
        contacts=[_contact_to_response(c) for c in contacts],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ContactResponse)
async def create_contact(
    request: ContactCreate,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> ContactResponse:
    """
    Create a new contact.

    If a contact with the same email already exists, the existing
    contact will be updated instead.
    """
    contacts_service = get_contacts_service(db)

    contact = await contacts_service.upsert_contact(
        current_user.organization_id,  # REM-003: Access as attribute
        email=request.email,
        phone=request.phone,
        full_name=request.full_name,
        contact_type=request.contact_type,
        company=request.company,
        metadata={"notes": request.notes} if request.notes else None,
    )

    # Add tags
    if request.tags:
        for tag in request.tags:
            await contacts_service.add_tag(
                contact.id,
                current_user.organization_id,  # REM-003: Access as attribute
                tag,
            )

    await db.commit()

    return _contact_to_response(contact)


@router.get("/repeat-clients")
async def get_repeat_clients(
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
    min_transactions: int = Query(2, ge=2),
    limit: int = Query(20, le=50),
) -> dict[str, Any]:
    """
    Get contacts with multiple transactions (VIP/repeat clients).
    """
    contacts_service = get_contacts_service(db)

    contacts = await contacts_service.get_repeat_clients(
        current_user.organization_id,  # REM-003: Access as attribute
        min_transactions=min_transactions,
        limit=limit,
    )

    return {
        "contacts": [_contact_to_response(c) for c in contacts],
        "total": len(contacts),
        "min_transactions": min_transactions,
    }


@router.get("/recent")
async def get_recent_contacts(
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
    limit: int = Query(10, le=50),
) -> dict[str, Any]:
    """
    Get most recently updated/created contacts.
    """
    contacts_service = get_contacts_service(db)

    contacts = await contacts_service.get_recent_contacts(
        current_user.organization_id,  # REM-003: Access as attribute
        limit=limit,
    )

    return {
        "contacts": [_contact_to_response(c) for c in contacts],
        "total": len(contacts),
    }


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> ContactResponse:
    """
    Get a contact by ID.
    """
    contacts_service = get_contacts_service(db)

    contact = await contacts_service.get_contact(
        contact_id,
        current_user.organization_id,  # REM-003: Access as attribute
    )

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return _contact_to_response(contact)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    request: ContactUpdate,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> ContactResponse:
    """
    Update a contact's information.
    """
    contacts_service = get_contacts_service(db)

    contact = await contacts_service.get_contact(
        contact_id,
        current_user.organization_id,  # REM-003: Access as attribute
    )

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Update fields
    if request.full_name:
        contact.full_name = request.full_name
    if request.email:
        contact.email = request.email
    if request.phone:
        contact.phone = request.phone
    if request.contact_type:
        contact.contact_type = request.contact_type
    if request.company:
        contact.company = request.company
    if request.notes:
        contact.notes = request.notes

    contact.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return _contact_to_response(contact)


@router.get("/{contact_id}/transactions")
async def get_contact_transactions(
    contact_id: UUID,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> dict[str, Any]:
    """
    Get all transactions involving a contact.

    Returns transactions where this contact appears as a party.
    """
    contacts_service = get_contacts_service(db)

    contact = await contacts_service.get_contact(
        contact_id,
        current_user.organization_id,  # REM-003: Access as attribute
    )

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    transactions = await contacts_service.get_contact_transactions(
        contact_id,
        current_user.organization_id,  # REM-003: Access as attribute
    )

    return {
        "contact_id": str(contact_id),
        "contact_name": contact.full_name,
        "transactions": transactions,
        "total": len(transactions),
    }


@router.post("/{contact_id}/tags/{tag}")
async def add_tag(
    contact_id: UUID,
    tag: str,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> ContactResponse:
    """
    Add a tag to a contact.
    """
    contacts_service = get_contacts_service(db)

    contact = await contacts_service.add_tag(
        contact_id,
        current_user.organization_id,  # REM-003: Access as attribute
        tag,
    )

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.commit()
    return _contact_to_response(contact)


@router.delete("/{contact_id}/tags/{tag}")
async def remove_tag(
    contact_id: UUID,
    tag: str,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> ContactResponse:
    """
    Remove a tag from a contact.
    """
    contacts_service = get_contacts_service(db)

    contact = await contacts_service.remove_tag(
        contact_id,
        current_user.organization_id,  # REM-003: Access as attribute
        tag,
    )

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.commit()
    return _contact_to_response(contact)


@router.post("/{contact_id}/notes")
async def add_note(
    contact_id: UUID,
    note: str = Query(..., description="Note text"),
    db: DbSessionDep = None,  # REM-003: Use typed dependency
    current_user: CurrentUserDep = None,  # REM-003: Use typed CurrentUserDep
) -> ContactResponse:
    """
    Add a note to a contact.
    """
    contacts_service = get_contacts_service(db)

    contact = await contacts_service.add_note(
        contact_id,
        current_user.organization_id,  # REM-003: Access as attribute
        note,
    )

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.commit()
    return _contact_to_response(contact)


@router.post("/sync-from-transaction/{transaction_id}")
async def sync_contacts_from_transaction(
    transaction_id: UUID,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> dict[str, Any]:
    """
    Sync contacts from transaction parties.

    Creates or updates contacts based on the parties in a transaction.
    """
    from packages.core.services import TransactionService

    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        transaction_id,
        current_user.organization_id,  # REM-003: Access as attribute
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    contacts_service = get_contacts_service(db)

    contacts = await contacts_service.sync_parties_to_contacts(
        transaction_id,
        current_user.organization_id,  # REM-003: Access as attribute
        transaction.parties or [],
    )

    await db.commit()

    return {
        "transaction_id": str(transaction_id),
        "synced_contacts": [_contact_to_response(c) for c in contacts],
        "total": len(contacts),
    }
