"""Transaction service - business logic for transaction management."""

from datetime import date
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import TransactionStatus, TransactionType
from packages.compliance.florida import FloridaComplianceEngine
from packages.db.repositories.transaction import TransactionRepository
from packages.db.repositories.deadline import DeadlineRepository
from packages.db.models import TransactionModel, ChecklistModel


class TransactionService:
    """
    Service for transaction business logic.

    Handles:
    - Transaction creation with checklist initialization
    - Status transitions with validation
    - Party management
    - Transaction queries with business rules
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transaction_repo = TransactionRepository(session)
        self.deadline_repo = DeadlineRepository(session)

    async def create_transaction(
        self,
        *,
        organization_id: UUID,
        created_by: UUID,
        transaction_type: str,
        property_address: dict[str, str],
        purchase_price: Decimal | None = None,
        year_built: int | None = None,
        closing_date: date | None = None,
        parties: list[dict[str, Any]] | None = None,
        notes: str | None = None,
    ) -> TransactionModel:
        """
        Create a new transaction with initialized checklist.

        Creates the transaction in 'draft' status and initializes
        a Florida compliance checklist based on property characteristics.
        """
        # Ensure all parties have unique IDs
        parties_with_ids = []
        for party in (parties or []):
            if not party.get("id"):
                party = {**party, "id": str(uuid4())}
            parties_with_ids.append(party)

        # Create transaction
        transaction = await self.transaction_repo.create(
            id=uuid4(),
            organization_id=organization_id,
            created_by=created_by,
            transaction_type=transaction_type,
            property_address=property_address,
            purchase_price=purchase_price,
            year_built=year_built,
            closing_date=closing_date,
            status=TransactionStatus.DRAFT,
            notes=notes,
            parties=parties_with_ids,
        )

        # Initialize FL checklist
        await self._initialize_checklist(
            transaction_id=transaction.id,
            year_built=year_built,
            is_financed=True,  # Default assumption
        )

        return transaction

    async def _initialize_checklist(
        self,
        transaction_id: UUID,
        year_built: int | None,
        is_financed: bool = True,
        is_hoa: bool = False,
    ) -> ChecklistModel:
        """Initialize Florida compliance checklist for transaction."""
        requirements = FloridaComplianceEngine.get_residential_purchase_checklist(
            property_year_built=year_built,
            is_hoa=is_hoa,
            is_financed=is_financed,
        )

        items = [
            {
                "id": str(uuid4()),
                "requirement_id": req.id,
                "name": req.name,
                "description": req.description,
                "category": req.category.value,
                "required": req.required,
                "status": "not_started",
                "document_id": None,
            }
            for req in requirements
        ]

        checklist = ChecklistModel(
            id=uuid4(),
            transaction_id=transaction_id,
            template_id="FL_RESIDENTIAL_PURCHASE",
            items=items,
        )

        self.session.add(checklist)
        await self.session.flush()

        return checklist

    async def get_transaction(
        self,
        transaction_id: UUID,
        organization_id: UUID,
    ) -> TransactionModel | None:
        """Get a transaction with access control."""
        transaction = await self.transaction_repo.get_with_relations(transaction_id)

        if not transaction:
            return None

        # Verify organization access
        if transaction.organization_id != organization_id:
            return None

        return transaction

    async def list_transactions(
        self,
        organization_id: UUID,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[TransactionModel], int]:
        """List transactions with pagination."""
        offset = (page - 1) * page_size

        transactions = await self.transaction_repo.get_by_organization(
            organization_id,
            status=status,
            offset=offset,
            limit=page_size,
        )

        total = await self.transaction_repo.count_by_organization(
            organization_id,
            status=status,
        )

        return transactions, total

    async def update_transaction(
        self,
        transaction_id: UUID,
        organization_id: UUID,
        *,
        status: str | None = None,
        purchase_price: Decimal | None = None,
        effective_date: date | None = None,
        closing_date: date | None = None,
        parties: list[dict] | None = None,
        notes: str | None = None,
    ) -> TransactionModel | None:
        """Update transaction with validation."""
        transaction = await self.get_transaction(transaction_id, organization_id)
        if not transaction:
            return None

        # Validate status transition
        if status:
            if not self._is_valid_status_transition(transaction.status, status):
                raise ValueError(f"Invalid status transition: {transaction.status} -> {status}")

        # Build update dict
        updates: dict[str, Any] = {}
        if status:
            updates["status"] = status
        if purchase_price is not None:
            updates["purchase_price"] = purchase_price
        if effective_date:
            updates["effective_date"] = effective_date
        if closing_date:
            updates["closing_date"] = closing_date
        if parties is not None:
            updates["parties"] = parties
        if notes is not None:
            updates["notes"] = notes

        if updates:
            return await self.transaction_repo.update(transaction_id, **updates)

        return transaction

    def _is_valid_status_transition(self, current: str, new: str) -> bool:
        """Validate status transition is allowed."""
        allowed_transitions = {
            TransactionStatus.DRAFT: [
                TransactionStatus.PENDING,
                TransactionStatus.CANCELLED,
            ],
            TransactionStatus.PENDING: [
                TransactionStatus.ACTIVE,
                TransactionStatus.CANCELLED,
                TransactionStatus.ON_HOLD,
            ],
            TransactionStatus.ACTIVE: [
                TransactionStatus.PENDING_CLOSE,
                TransactionStatus.CANCELLED,
                TransactionStatus.ON_HOLD,
            ],
            TransactionStatus.PENDING_CLOSE: [
                TransactionStatus.CLOSED,
                TransactionStatus.ACTIVE,
                TransactionStatus.CANCELLED,
            ],
            TransactionStatus.ON_HOLD: [
                TransactionStatus.ACTIVE,
                TransactionStatus.CANCELLED,
            ],
            TransactionStatus.CLOSED: [],  # Terminal state
            TransactionStatus.CANCELLED: [],  # Terminal state
        }

        current_status = TransactionStatus(current)
        new_status = TransactionStatus(new)

        return new_status in allowed_transitions.get(current_status, [])

    async def add_party(
        self,
        transaction_id: UUID,
        organization_id: UUID,
        party: dict[str, Any],
    ) -> TransactionModel | None:
        """Add a party to the transaction."""
        transaction = await self.get_transaction(transaction_id, organization_id)
        if not transaction:
            return None

        parties = list(transaction.parties or [])

        # Add ID if not present
        if "id" not in party:
            party["id"] = str(uuid4())

        parties.append(party)

        return await self.transaction_repo.update(transaction_id, parties=parties)

    async def remove_party(
        self,
        transaction_id: UUID,
        organization_id: UUID,
        party_id: str,
    ) -> TransactionModel | None:
        """Remove a party from the transaction."""
        transaction = await self.get_transaction(transaction_id, organization_id)
        if not transaction:
            return None

        parties = [p for p in (transaction.parties or []) if p.get("id") != party_id]

        return await self.transaction_repo.update(transaction_id, parties=parties)

    async def delete_transaction(
        self,
        transaction_id: UUID,
        organization_id: UUID,
        deleted_by: UUID | None = None,
    ) -> bool:
        """
        Delete a draft transaction.

        Args:
            transaction_id: ID of the transaction to delete
            organization_id: Organization ID for access control
            deleted_by: ID of the user performing the deletion (for audit trail)
        """
        transaction = await self.get_transaction(transaction_id, organization_id)
        if not transaction:
            return False

        # Only allow deleting draft transactions
        if transaction.status != TransactionStatus.DRAFT:
            raise ValueError("Can only delete draft transactions")

        # Use soft delete if available and deleted_by provided
        if hasattr(self.transaction_repo, 'soft_delete') and deleted_by:
            return await self.transaction_repo.soft_delete(transaction_id, deleted_by)
        return await self.transaction_repo.delete(transaction_id)

    async def get_dashboard_summary(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """Get transaction summary for dashboard."""
        active = await self.transaction_repo.count_by_organization(
            organization_id, status=TransactionStatus.ACTIVE
        )
        pending = await self.transaction_repo.count_by_organization(
            organization_id, status=TransactionStatus.PENDING
        )
        pending_close = await self.transaction_repo.count_by_organization(
            organization_id, status=TransactionStatus.PENDING_CLOSE
        )
        closed_this_month = await self.transaction_repo.count_closed_this_month(
            organization_id
        )

        upcoming_closings = await self.transaction_repo.get_active_with_upcoming_closing(
            organization_id, within_days=14
        )

        return {
            "active_transactions": active + pending_close,
            "pending_review": pending,
            "closing_soon": len(upcoming_closings),
            "closed_this_month": closed_this_month,
            "upcoming_closings": [
                {
                    "id": str(t.id),
                    "address": t.property_address.get("street", ""),
                    "closing_date": str(t.closing_date) if t.closing_date else None,
                }
                for t in upcoming_closings[:5]
            ],
        }
