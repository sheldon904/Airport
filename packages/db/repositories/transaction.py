"""Transaction repository."""

from datetime import date
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from packages.db.models import TransactionModel, DocumentModel, DeadlineModel, ChecklistModel
from packages.db.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[TransactionModel]):
    """Repository for transaction operations."""

    model = TransactionModel

    async def get_with_relations(self, id: UUID) -> TransactionModel | None:
        """Get transaction with all related entities loaded."""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.id == id)
            .options(
                selectinload(self.model.documents),
                selectinload(self.model.deadlines),
                selectinload(self.model.checklist),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_organization(
        self,
        organization_id: UUID,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[TransactionModel]:
        """Get transactions for an organization with optional status filter."""
        query = select(self.model).where(
            self.model.organization_id == organization_id
        )

        if status:
            query = query.where(self.model.status == status)

        query = query.order_by(self.model.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_user(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> Sequence[TransactionModel]:
        """Get transactions created by a specific user."""
        query = select(self.model).where(self.model.created_by == user_id)

        if status:
            query = query.where(self.model.status == status)

        query = query.order_by(self.model.created_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_with_upcoming_closing(
        self,
        organization_id: UUID,
        within_days: int = 30,
    ) -> Sequence[TransactionModel]:
        """Get active transactions with closing dates within N days."""
        today = date.today()
        future_date = date.today().replace(day=today.day + within_days)

        result = await self.session.execute(
            select(self.model)
            .where(
                and_(
                    self.model.organization_id == organization_id,
                    self.model.status == "active",
                    self.model.closing_date != None,
                    self.model.closing_date <= future_date,
                    self.model.closing_date >= today,
                )
            )
            .order_by(self.model.closing_date)
        )
        return result.scalars().all()

    async def update_status(self, id: UUID, status: str) -> TransactionModel | None:
        """Update transaction status."""
        return await self.update(id, status=status)

    async def update_dates(
        self,
        id: UUID,
        effective_date: date | None = None,
        closing_date: date | None = None,
    ) -> TransactionModel | None:
        """Update transaction key dates."""
        updates = {}
        if effective_date:
            updates["effective_date"] = effective_date
        if closing_date:
            updates["closing_date"] = closing_date

        if updates:
            return await self.update(id, **updates)
        return await self.get_by_id(id)

    async def count_by_organization(
        self,
        organization_id: UUID,
        *,
        status: str | None = None,
    ) -> int:
        """Count transactions for an organization."""
        filters = {"organization_id": organization_id}
        if status:
            filters["status"] = status
        return await self.count(**filters)
