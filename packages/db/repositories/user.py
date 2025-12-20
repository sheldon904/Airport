"""User repository."""

from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import select

from packages.db.models import UserModel
from packages.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Repository for user operations."""

    model = UserModel

    async def get_by_email(self, email: str) -> UserModel | None:
        """Find user by email address."""
        return await self.find_one_by(email=email.lower())

    async def get_by_organization(
        self,
        organization_id: UUID,
        *,
        active_only: bool = True,
    ) -> Sequence[UserModel]:
        """Get all users in an organization."""
        query = select(self.model).where(
            self.model.organization_id == organization_id
        )

        if active_only:
            query = query.where(self.model.is_active == True)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        await self.update(user_id, last_login_at=datetime.utcnow())

    async def verify_email(self, user_id: UUID) -> UserModel | None:
        """Mark user's email as verified."""
        return await self.update(user_id, email_verified=True)

    async def deactivate(self, user_id: UUID) -> UserModel | None:
        """Deactivate a user account."""
        return await self.update(user_id, is_active=False)
