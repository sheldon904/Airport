"""Contacts service - lightweight CRM functionality."""

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import ContactModel, TransactionModel


class ContactType:
    """Contact type constants."""

    BUYER = "buyer"
    SELLER = "seller"
    BUYER_AGENT = "buyer_agent"
    SELLER_AGENT = "seller_agent"
    LENDER = "lender"
    TITLE_COMPANY = "title_company"
    INSPECTOR = "inspector"
    APPRAISER = "appraiser"
    ATTORNEY = "attorney"
    OTHER = "other"


class ContactSource:
    """Contact source constants."""

    MANUAL = "manual"
    EXTRACTION = "extraction"
    CRM_SYNC = "crm_sync"
    IMPORT = "import"


class ContactsService:
    """
    Service for managing contacts (lightweight CRM).

    Handles:
    - Creating and managing contacts
    - Deduplicating contacts by email
    - Tracking contact interactions across transactions
    - Searching and filtering contacts
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_contact(
        self,
        organization_id: UUID,
        *,
        email: str | None = None,
        phone: str | None = None,
        full_name: str,
        contact_type: str = ContactType.OTHER,
        company: str | None = None,
        source: str = ContactSource.MANUAL,
        transaction_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ContactModel:
        """
        Create or update a contact.

        Deduplicates by email within organization.

        Args:
            organization_id: Organization ID
            email: Contact email (used for deduplication)
            phone: Contact phone
            full_name: Contact full name
            contact_type: Type of contact (buyer, seller, agent, etc.)
            company: Company name
            source: How the contact was created
            transaction_id: Associated transaction (for tracking)
            metadata: Additional metadata

        Returns:
            Created or updated ContactModel
        """
        existing = None

        # Check for existing contact by email
        if email:
            stmt = select(ContactModel).where(
                and_(
                    ContactModel.organization_id == organization_id,
                    ContactModel.email == email,
                )
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

        if existing:
            # Update existing contact
            if full_name:
                existing.full_name = full_name
            if phone:
                existing.phone = phone
            if company:
                existing.company = company
            if contact_type != ContactType.OTHER:
                existing.contact_type = contact_type
            if transaction_id:
                existing.last_transaction_id = transaction_id
                existing.last_transaction_date = datetime.now().date()
                existing.transaction_count = (existing.transaction_count or 0) + 1
            if metadata:
                existing.extra_data = {**(existing.extra_data or {}), **metadata}

            existing.updated_at = datetime.now()
            await self.session.flush()
            return existing

        # Create new contact
        contact = ContactModel(
            id=uuid4(),
            organization_id=organization_id,
            email=email,
            phone=phone,
            full_name=full_name,
            contact_type=contact_type,
            company=company,
            source=source,
            transaction_count=1 if transaction_id else 0,
            last_transaction_id=transaction_id,
            last_transaction_date=datetime.now().date() if transaction_id else None,
            extra_data=metadata or {},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.session.add(contact)
        await self.session.flush()

        return contact

    async def get_contact(
        self,
        contact_id: UUID,
        organization_id: UUID,
    ) -> ContactModel | None:
        """Get a contact by ID."""
        stmt = select(ContactModel).where(
            and_(
                ContactModel.id == contact_id,
                ContactModel.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_contact_by_email(
        self,
        email: str,
        organization_id: UUID,
    ) -> ContactModel | None:
        """Get a contact by email."""
        stmt = select(ContactModel).where(
            and_(
                ContactModel.email == email,
                ContactModel.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_contacts(
        self,
        organization_id: UUID,
        *,
        query: str | None = None,
        contact_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[ContactModel], int]:
        """
        Search contacts with optional filters.

        Args:
            organization_id: Organization ID
            query: Search query (matches name, email, phone, company)
            contact_type: Filter by contact type
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            tuple: (contacts, total_count)
        """
        conditions = [ContactModel.organization_id == organization_id]

        if contact_type:
            conditions.append(ContactModel.contact_type == contact_type)

        if query:
            search_term = f"%{query}%"
            conditions.append(
                or_(
                    ContactModel.full_name.ilike(search_term),
                    ContactModel.email.ilike(search_term),
                    ContactModel.phone.ilike(search_term),
                    ContactModel.company.ilike(search_term),
                )
            )

        # Get count
        count_stmt = select(func.count()).select_from(ContactModel).where(and_(*conditions))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get contacts
        stmt = (
            select(ContactModel)
            .where(and_(*conditions))
            .order_by(ContactModel.full_name)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        contacts = result.scalars().all()

        return contacts, total

    async def get_contact_transactions(
        self,
        contact_id: UUID,
        organization_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        Get all transactions involving a contact.

        Returns list of transactions with the contact's role in each.
        """
        # Get contact
        contact = await self.get_contact(contact_id, organization_id)
        if not contact or not contact.email:
            return []

        # Search transactions for this contact's email in parties
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.organization_id == organization_id,
                TransactionModel.deleted_at.is_(None),
            )
        ).order_by(TransactionModel.created_at.desc())

        result = await self.session.execute(stmt)
        transactions = result.scalars().all()

        # Filter to transactions containing this contact
        contact_transactions = []
        for tx in transactions:
            for party in (tx.parties or []):
                if party.get("email") == contact.email:
                    contact_transactions.append({
                        "transaction_id": str(tx.id),
                        "property_address": tx.property_address.get("street", "") if tx.property_address else "",
                        "city": tx.property_address.get("city", "") if tx.property_address else "",
                        "role": party.get("role"),
                        "status": tx.status,
                        "closing_date": str(tx.closing_date) if tx.closing_date else None,
                        "purchase_price": float(tx.purchase_price) if tx.purchase_price else None,
                        "created_at": tx.created_at.isoformat() if tx.created_at else None,
                    })
                    break

        return contact_transactions

    async def sync_parties_to_contacts(
        self,
        transaction_id: UUID,
        organization_id: UUID,
        parties: list[dict[str, Any]],
    ) -> list[ContactModel]:
        """
        Create/update contacts from transaction parties.

        Called after document extraction or party updates to keep contacts in sync.

        Returns:
            List of created/updated contacts
        """
        contacts = []

        for party in parties:
            email = party.get("email")
            name = party.get("name")
            role = party.get("role", ContactType.OTHER)

            if not name:
                continue

            contact = await self.upsert_contact(
                organization_id,
                email=email,
                phone=party.get("phone"),
                full_name=name,
                contact_type=role,
                company=party.get("company"),
                source=ContactSource.EXTRACTION,
                transaction_id=transaction_id,
                metadata={
                    "license_number": party.get("license_number"),
                },
            )
            contacts.append(contact)

        return contacts

    async def get_repeat_clients(
        self,
        organization_id: UUID,
        min_transactions: int = 2,
        limit: int = 20,
    ) -> Sequence[ContactModel]:
        """
        Get contacts with multiple transactions (repeat clients).

        Useful for identifying VIP clients.
        """
        stmt = (
            select(ContactModel)
            .where(
                and_(
                    ContactModel.organization_id == organization_id,
                    ContactModel.transaction_count >= min_transactions,
                )
            )
            .order_by(ContactModel.transaction_count.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recent_contacts(
        self,
        organization_id: UUID,
        limit: int = 10,
    ) -> Sequence[ContactModel]:
        """Get most recently updated/created contacts."""
        stmt = (
            select(ContactModel)
            .where(ContactModel.organization_id == organization_id)
            .order_by(ContactModel.updated_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_note(
        self,
        contact_id: UUID,
        organization_id: UUID,
        note: str,
    ) -> ContactModel | None:
        """Add a note to a contact's metadata."""
        contact = await self.get_contact(contact_id, organization_id)
        if not contact:
            return None

        notes = contact.extra_data.get("notes", []) if contact.extra_data else []
        notes.append({
            "text": note,
            "created_at": datetime.now().isoformat(),
        })

        contact.extra_data = {**(contact.extra_data or {}), "notes": notes}
        contact.updated_at = datetime.now()
        await self.session.flush()

        return contact

    async def add_tag(
        self,
        contact_id: UUID,
        organization_id: UUID,
        tag: str,
    ) -> ContactModel | None:
        """Add a tag to a contact."""
        contact = await self.get_contact(contact_id, organization_id)
        if not contact:
            return None

        tags = contact.tags or []
        if tag not in tags:
            tags.append(tag)
            contact.tags = tags
            contact.updated_at = datetime.now()
            await self.session.flush()

        return contact

    async def remove_tag(
        self,
        contact_id: UUID,
        organization_id: UUID,
        tag: str,
    ) -> ContactModel | None:
        """Remove a tag from a contact."""
        contact = await self.get_contact(contact_id, organization_id)
        if not contact:
            return None

        tags = contact.tags or []
        if tag in tags:
            tags.remove(tag)
            contact.tags = tags
            contact.updated_at = datetime.now()
            await self.session.flush()

        return contact


def get_contacts_service(session: AsyncSession) -> ContactsService:
    """Factory function for ContactsService."""
    return ContactsService(session)
