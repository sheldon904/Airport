"""Deadline service - business logic for deadline management."""

from datetime import date, timedelta
from typing import Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import DeadlineType, DeadlineStatus
from packages.db.repositories.deadline import DeadlineRepository
from packages.db.repositories.transaction import TransactionRepository
from packages.db.models import DeadlineModel


class DeadlineService:
    """
    Service for deadline business logic.

    Handles:
    - Deadline creation from extracted data
    - Status updates and notifications
    - Completion and waiver workflows
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.deadline_repo = DeadlineRepository(session)
        self.transaction_repo = TransactionRepository(session)

    async def create_deadline(
        self,
        *,
        transaction_id: UUID,
        organization_id: UUID,
        deadline_type: str,
        name: str,
        due_date: date,
        description: str | None = None,
        source_document_id: UUID | None = None,
        reminder_days: list[int] | None = None,
    ) -> DeadlineModel:
        """Create a new deadline."""
        # Verify transaction access
        transaction = await self.transaction_repo.get_by_id(transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            raise ValueError("Transaction not found or access denied")

        return await self.deadline_repo.create(
            id=uuid4(),
            transaction_id=transaction_id,
            deadline_type=deadline_type,
            name=name,
            due_date=due_date,
            description=description,
            source_document_id=source_document_id,
            reminder_days=reminder_days or [7, 3, 1],
            status=self._calculate_status(due_date),
        )

    async def create_deadlines_from_extraction(
        self,
        transaction_id: UUID,
        extracted_deadlines: list[dict[str, Any]],
        source_document_id: UUID,
    ) -> list[DeadlineModel]:
        """
        Create deadlines from document extraction results.

        Called by the orchestrator after document extraction.
        """
        created = []

        for deadline_data in extracted_deadlines:
            deadline = await self.deadline_repo.create(
                id=uuid4(),
                transaction_id=transaction_id,
                deadline_type=deadline_data.get("deadline_type", DeadlineType.CUSTOM),
                name=deadline_data["name"],
                due_date=deadline_data["due_date"],
                description=deadline_data.get("description"),
                source_document_id=source_document_id,
                reminder_days=deadline_data.get("reminder_days", [7, 3, 1]),
                status=self._calculate_status(deadline_data["due_date"]),
            )
            created.append(deadline)

        return created

    def _calculate_status(self, due_date: date) -> str:
        """Calculate deadline status based on due date."""
        today = date.today()
        days_until = (due_date - today).days

        if days_until < 0:
            return DeadlineStatus.OVERDUE
        elif days_until <= 3:
            return DeadlineStatus.DUE_SOON
        else:
            return DeadlineStatus.UPCOMING

    async def get_deadline(
        self,
        deadline_id: UUID,
        organization_id: UUID,
    ) -> DeadlineModel | None:
        """Get a single deadline with access control."""
        deadline = await self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            return None

        # Verify access through transaction
        transaction = await self.transaction_repo.get_by_id(deadline.transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return None

        return deadline

    async def get_transaction_deadlines(
        self,
        transaction_id: UUID,
        organization_id: UUID,
        *,
        include_completed: bool = False,
    ) -> list[DeadlineModel]:
        """Get deadlines for a transaction."""
        # Verify access
        transaction = await self.transaction_repo.get_by_id(transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return []

        deadlines = await self.deadline_repo.get_by_transaction(
            transaction_id,
            include_completed=include_completed,
        )
        return list(deadlines)

    # Florida statutory deadlines
    STATUTORY_DEADLINE_TYPES = {
        "inspection_period",
        "financing_contingency",
        "title_review",
        "hoa_disclosure_review",
        "lead_paint_disclosure",
        "right_to_cancel",
    }

    async def get_upcoming_deadlines(
        self,
        organization_id: UUID,
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Get upcoming deadlines across all transactions.

        Returns enriched deadline data with transaction info.
        Uses eager loading to avoid N+1 query problem.
        """
        # Use eager loading to fetch transactions in a single query
        deadlines = await self.deadline_repo.get_upcoming(
            organization_id=organization_id,
            days_ahead=days_ahead,
            load_transaction=True,
        )

        result = []
        for deadline in deadlines:
            # Transaction is already loaded via eager loading
            transaction = deadline.transaction
            if transaction and transaction.organization_id == organization_id:
                days_remaining = (deadline.due_date - date.today()).days
                is_statutory = deadline.deadline_type in self.STATUTORY_DEADLINE_TYPES
                result.append({
                    "id": str(deadline.id),
                    "name": deadline.name,
                    "title": deadline.name,  # Alias for frontend compatibility
                    "due_date": str(deadline.due_date),
                    "days_remaining": days_remaining,
                    "status": deadline.status,
                    "deadline_type": deadline.deadline_type,
                    "transaction_id": str(transaction.id),
                    "property_address": transaction.property_address.get("street", ""),
                    "is_statutory": is_statutory,
                })

        return sorted(result, key=lambda x: x["due_date"])

    async def get_overdue_deadlines(
        self,
        organization_id: UUID,
    ) -> list[DeadlineModel]:
        """Get all overdue deadlines."""
        deadlines = await self.deadline_repo.get_overdue(organization_id)
        return list(deadlines)

    async def complete_deadline(
        self,
        deadline_id: UUID,
        organization_id: UUID,
        completed_by: UUID,
        notes: str | None = None,
    ) -> DeadlineModel | None:
        """Mark a deadline as completed."""
        deadline = await self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            return None

        # Verify access
        transaction = await self.transaction_repo.get_by_id(deadline.transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return None

        return await self.deadline_repo.mark_completed(
            deadline_id,
            completed_by=completed_by,
            notes=notes,
        )

    async def waive_deadline(
        self,
        deadline_id: UUID,
        organization_id: UUID,
        reason: str,
    ) -> DeadlineModel | None:
        """Waive a deadline (e.g., buyer waives inspection)."""
        deadline = await self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            return None

        # Verify access
        transaction = await self.transaction_repo.get_by_id(deadline.transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return None

        if not reason:
            raise ValueError("Reason is required for waiving a deadline")

        return await self.deadline_repo.mark_waived(deadline_id, reason)

    async def extend_deadline(
        self,
        deadline_id: UUID,
        organization_id: UUID,
        new_date: date,
        reason: str | None = None,
    ) -> DeadlineModel | None:
        """Extend a deadline to a new date."""
        deadline = await self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            return None

        # Verify access
        transaction = await self.transaction_repo.get_by_id(deadline.transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return None

        # Validate new date is in the future
        if new_date <= date.today():
            raise ValueError("New date must be in the future")

        return await self.deadline_repo.extend(deadline_id, new_date, reason)

    async def update_deadline(
        self,
        deadline_id: UUID,
        organization_id: UUID,
        *,
        due_date: date | None = None,
        name: str | None = None,
        notes: str | None = None,
    ) -> DeadlineModel | None:
        """Update deadline details."""
        deadline = await self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            return None

        # Verify access
        transaction = await self.transaction_repo.get_by_id(deadline.transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return None

        updates: dict[str, Any] = {}
        if due_date:
            updates["due_date"] = due_date
            updates["status"] = self._calculate_status(due_date)
        if name:
            updates["name"] = name
        if notes is not None:
            updates["notes"] = notes

        if updates:
            return await self.deadline_repo.update(deadline_id, **updates)

        return deadline

    async def delete_deadline(
        self,
        deadline_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """Delete a custom deadline."""
        deadline = await self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            return False

        # Verify access
        transaction = await self.transaction_repo.get_by_id(deadline.transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return False

        # Only allow deleting custom deadlines
        if deadline.deadline_type != DeadlineType.CUSTOM:
            raise ValueError("Can only delete custom deadlines")

        return await self.deadline_repo.delete(deadline_id)

    async def update_all_statuses(self) -> int:
        """
        Update status of all deadlines based on current date.

        Called by background worker daily.
        """
        return await self.deadline_repo.update_statuses()

    async def get_reminders_due(self) -> list[dict[str, Any]]:
        """
        Get deadlines that need reminder notifications today.

        Called by background worker to send reminders.
        Uses eager loading to avoid N+1 query problem.
        """
        today = date.today()
        # Use eager loading to fetch transactions in a single query
        deadlines = await self.deadline_repo.get_needing_reminder(
            today,
            load_transaction=True,
        )

        reminders = []
        for deadline in deadlines:
            # Transaction is already loaded via eager loading
            transaction = deadline.transaction
            if transaction:
                days_until = (deadline.due_date - today).days
                reminders.append({
                    "deadline_id": str(deadline.id),
                    "deadline_name": deadline.name,
                    "due_date": str(deadline.due_date),
                    "days_remaining": days_until,
                    "transaction_id": str(transaction.id),
                    "organization_id": str(transaction.organization_id),
                    "property_address": transaction.property_address,
                })

        return reminders
