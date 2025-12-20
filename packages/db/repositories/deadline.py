"""Deadline repository."""

from datetime import date, datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, select

from packages.db.models import DeadlineModel
from packages.db.repositories.base import BaseRepository


class DeadlineRepository(BaseRepository[DeadlineModel]):
    """Repository for deadline operations."""

    model = DeadlineModel

    async def get_by_transaction(
        self,
        transaction_id: UUID,
        *,
        include_completed: bool = False,
    ) -> Sequence[DeadlineModel]:
        """Get all deadlines for a transaction."""
        query = select(self.model).where(
            self.model.transaction_id == transaction_id
        )

        if not include_completed:
            query = query.where(
                self.model.status.notin_(["completed", "waived"])
            )

        query = query.order_by(self.model.due_date)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_upcoming(
        self,
        organization_id: UUID | None = None,
        days_ahead: int = 7,
    ) -> Sequence[DeadlineModel]:
        """Get upcoming deadlines within N days."""
        today = date.today()
        future = date.today().replace(day=today.day + days_ahead)

        query = select(self.model).where(
            and_(
                self.model.due_date >= today,
                self.model.due_date <= future,
                self.model.status.in_(["upcoming", "due_soon"]),
            )
        )

        # TODO: Join with transactions to filter by org

        query = query.order_by(self.model.due_date)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_overdue(
        self,
        organization_id: UUID | None = None,
    ) -> Sequence[DeadlineModel]:
        """Get all overdue deadlines."""
        today = date.today()

        query = select(self.model).where(
            and_(
                self.model.due_date < today,
                self.model.status.in_(["upcoming", "due_soon", "overdue"]),
            )
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_needing_reminder(
        self,
        target_date: date,
    ) -> Sequence[DeadlineModel]:
        """Get deadlines that need a reminder sent today."""
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.due_date > target_date,
                    self.model.status.in_(["upcoming", "due_soon"]),
                )
            )
        )

        deadlines = result.scalars().all()

        # Filter by reminder days
        needs_reminder = []
        for deadline in deadlines:
            days_until = (deadline.due_date - target_date).days
            if days_until in (deadline.reminder_days or [7, 3, 1]):
                needs_reminder.append(deadline)

        return needs_reminder

    async def mark_completed(
        self,
        deadline_id: UUID,
        completed_by: UUID,
        notes: str | None = None,
    ) -> DeadlineModel | None:
        """Mark a deadline as completed."""
        return await self.update(
            deadline_id,
            status="completed",
            completed_at=datetime.utcnow(),
            completed_by=completed_by,
            notes=notes,
        )

    async def mark_waived(
        self,
        deadline_id: UUID,
        reason: str,
    ) -> DeadlineModel | None:
        """Mark a deadline as waived."""
        return await self.update(
            deadline_id,
            status="waived",
            notes=reason,
        )

    async def extend(
        self,
        deadline_id: UUID,
        new_date: date,
        reason: str | None = None,
    ) -> DeadlineModel | None:
        """Extend a deadline to a new date."""
        deadline = await self.get_by_id(deadline_id)
        if not deadline:
            return None

        existing_notes = deadline.notes or ""
        extension_note = f"Extended from {deadline.due_date} to {new_date}"
        if reason:
            extension_note += f": {reason}"

        new_notes = f"{existing_notes}\n{extension_note}".strip()

        return await self.update(
            deadline_id,
            due_date=new_date,
            status="extended",
            notes=new_notes,
        )

    async def bulk_create_for_transaction(
        self,
        transaction_id: UUID,
        deadlines: list[dict],
    ) -> list[DeadlineModel]:
        """Create multiple deadlines for a transaction."""
        created = []
        for deadline_data in deadlines:
            deadline = await self.create(
                transaction_id=transaction_id,
                **deadline_data,
            )
            created.append(deadline)
        return created

    async def update_statuses(self) -> int:
        """Update deadline statuses based on current date."""
        today = date.today()
        updated = 0

        # Get all active deadlines
        result = await self.session.execute(
            select(self.model).where(
                self.model.status.in_(["upcoming", "due_soon"])
            )
        )
        deadlines = result.scalars().all()

        for deadline in deadlines:
            days_until = (deadline.due_date - today).days

            if days_until < 0:
                await self.update(deadline.id, status="overdue")
                updated += 1
            elif days_until <= 3:
                if deadline.status != "due_soon":
                    await self.update(deadline.id, status="due_soon")
                    updated += 1

        return updated
