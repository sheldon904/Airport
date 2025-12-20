"""Organization repository."""

from packages.db.models import OrganizationModel
from packages.db.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[OrganizationModel]):
    """Repository for organization operations."""

    model = OrganizationModel

    async def get_by_license(self, license_number: str) -> OrganizationModel | None:
        """Find organization by license number."""
        return await self.find_one_by(license_number=license_number)

    async def get_active_organizations(self) -> list[OrganizationModel]:
        """Get all organizations with active subscriptions."""
        orgs = await self.find_by(subscription_status="active")
        return list(orgs)
