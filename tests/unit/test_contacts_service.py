"""Unit tests for contacts/CRM service."""

import pytest
from datetime import datetime, date
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from packages.core.services.contacts import (
    ContactsService,
    ContactType,
    ContactSource,
    get_contacts_service,
)


class TestContactConstants:
    """Tests for contact constants."""

    def test_contact_types_defined(self):
        """Contact types are defined."""
        assert ContactType.BUYER == "buyer"
        assert ContactType.SELLER == "seller"
        assert ContactType.BUYER_AGENT == "buyer_agent"
        assert ContactType.SELLER_AGENT == "seller_agent"
        assert ContactType.LENDER == "lender"
        assert ContactType.TITLE_COMPANY == "title_company"
        assert ContactType.INSPECTOR == "inspector"
        assert ContactType.APPRAISER == "appraiser"
        assert ContactType.ATTORNEY == "attorney"
        assert ContactType.OTHER == "other"

    def test_contact_sources_defined(self):
        """Contact sources are defined."""
        assert ContactSource.MANUAL == "manual"
        assert ContactSource.EXTRACTION == "extraction"
        assert ContactSource.CRM_SYNC == "crm_sync"
        assert ContactSource.IMPORT == "import"


class TestContactsService:
    """Tests for ContactsService methods."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return ContactsService(mock_session)

    @pytest.mark.asyncio
    async def test_upsert_contact_new(self, service, mock_session):
        """Creates new contact when not found."""
        # Mock no existing contact
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        org_id = uuid4()
        contact = await service.upsert_contact(
            org_id,
            email="john@example.com",
            full_name="John Doe",
            contact_type=ContactType.BUYER,
        )

        mock_session.add.assert_called_once()
        assert contact.full_name == "John Doe"
        assert contact.email == "john@example.com"
        assert contact.contact_type == ContactType.BUYER

    @pytest.mark.asyncio
    async def test_upsert_contact_existing(self, service, mock_session):
        """Updates existing contact when found by email."""
        # Mock existing contact
        existing = MagicMock()
        existing.full_name = "John Doe"
        existing.email = "john@example.com"
        existing.phone = None
        existing.company = None
        existing.contact_type = ContactType.OTHER
        existing.transaction_count = 1
        existing.extra_data = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        org_id = uuid4()
        contact = await service.upsert_contact(
            org_id,
            email="john@example.com",
            full_name="John Updated",
            phone="555-1234",
            contact_type=ContactType.BUYER,
        )

        # Should update existing
        assert contact.full_name == "John Updated"
        assert contact.phone == "555-1234"
        # Add was not called (updated existing)
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_contact_increments_transaction_count(self, service, mock_session):
        """Increments transaction count when transaction_id provided."""
        existing = MagicMock()
        existing.full_name = "John Doe"
        existing.email = "john@example.com"
        existing.phone = None
        existing.company = None
        existing.contact_type = ContactType.BUYER
        existing.transaction_count = 2
        existing.extra_data = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        org_id = uuid4()
        tx_id = uuid4()

        await service.upsert_contact(
            org_id,
            email="john@example.com",
            full_name="John Doe",
            transaction_id=tx_id,
        )

        assert existing.transaction_count == 3
        assert existing.last_transaction_id == tx_id

    @pytest.mark.asyncio
    async def test_get_contact_found(self, service, mock_session):
        """Returns contact when found."""
        mock_contact = MagicMock()
        mock_contact.id = uuid4()
        mock_contact.full_name = "John Doe"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_session.execute.return_value = mock_result

        result = await service.get_contact(uuid4(), uuid4())

        assert result is not None
        assert result.full_name == "John Doe"

    @pytest.mark.asyncio
    async def test_get_contact_not_found(self, service, mock_session):
        """Returns None when contact not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.get_contact(uuid4(), uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_contact_by_email(self, service, mock_session):
        """Retrieves contact by email."""
        mock_contact = MagicMock()
        mock_contact.email = "john@example.com"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_session.execute.return_value = mock_result

        result = await service.get_contact_by_email("john@example.com", uuid4())

        assert result is not None
        assert result.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_search_contacts(self, service, mock_session):
        """Searches contacts with filters."""
        mock_contacts = [MagicMock(), MagicMock()]

        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 2

        # Mock contacts query
        contacts_result = MagicMock()
        contacts_result.scalars.return_value.all.return_value = mock_contacts

        mock_session.execute.side_effect = [count_result, contacts_result]

        contacts, total = await service.search_contacts(
            uuid4(),
            query="john",
            contact_type=ContactType.BUYER,
            limit=10,
        )

        assert total == 2
        assert len(contacts) == 2

    @pytest.mark.asyncio
    async def test_add_tag(self, service, mock_session):
        """Adds tag to contact."""
        mock_contact = MagicMock()
        mock_contact.tags = ["existing"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_session.execute.return_value = mock_result

        await service.add_tag(uuid4(), uuid4(), "new_tag")

        assert "new_tag" in mock_contact.tags
        assert "existing" in mock_contact.tags

    @pytest.mark.asyncio
    async def test_add_tag_duplicate(self, service, mock_session):
        """Does not add duplicate tag."""
        mock_contact = MagicMock()
        mock_contact.tags = ["existing"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_session.execute.return_value = mock_result

        await service.add_tag(uuid4(), uuid4(), "existing")

        assert mock_contact.tags.count("existing") == 1

    @pytest.mark.asyncio
    async def test_remove_tag(self, service, mock_session):
        """Removes tag from contact."""
        mock_contact = MagicMock()
        mock_contact.tags = ["keep", "remove"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_session.execute.return_value = mock_result

        await service.remove_tag(uuid4(), uuid4(), "remove")

        assert "remove" not in mock_contact.tags
        assert "keep" in mock_contact.tags

    @pytest.mark.asyncio
    async def test_add_note(self, service, mock_session):
        """Adds note to contact extra_data."""
        mock_contact = MagicMock()
        mock_contact.extra_data = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_session.execute.return_value = mock_result

        await service.add_note(uuid4(), uuid4(), "This is a note")

        assert "notes" in mock_contact.extra_data
        assert len(mock_contact.extra_data["notes"]) == 1
        assert mock_contact.extra_data["notes"][0]["text"] == "This is a note"

    @pytest.mark.asyncio
    async def test_sync_parties_to_contacts(self, service, mock_session):
        """Syncs transaction parties to contacts."""
        # Mock no existing contacts
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        parties = [
            {"name": "John Buyer", "role": "buyer", "email": "john@example.com"},
            {"name": "Jane Seller", "role": "seller", "email": "jane@example.com"},
        ]

        contacts = await service.sync_parties_to_contacts(
            uuid4(), uuid4(), parties
        )

        assert len(contacts) == 2
        assert mock_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_parties_skips_no_name(self, service, mock_session):
        """Skips parties without names."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        parties = [
            {"name": "John Buyer", "role": "buyer"},
            {"role": "seller", "email": "no-name@example.com"},  # No name
        ]

        contacts = await service.sync_parties_to_contacts(
            uuid4(), uuid4(), parties
        )

        assert len(contacts) == 1

    @pytest.mark.asyncio
    async def test_get_repeat_clients(self, service, mock_session):
        """Gets repeat clients with multiple transactions."""
        mock_contacts = [
            MagicMock(transaction_count=5),
            MagicMock(transaction_count=3),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_contacts
        mock_session.execute.return_value = mock_result

        contacts = await service.get_repeat_clients(uuid4(), min_transactions=2)

        assert len(contacts) == 2

    @pytest.mark.asyncio
    async def test_get_recent_contacts(self, service, mock_session):
        """Gets recently updated contacts."""
        mock_contacts = [MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_contacts
        mock_session.execute.return_value = mock_result

        contacts = await service.get_recent_contacts(uuid4(), limit=10)

        assert len(contacts) == 2


class TestContactsServiceFactory:
    """Tests for service factory."""

    def test_get_contacts_service(self):
        """Factory returns service instance."""
        mock_session = MagicMock()
        service = get_contacts_service(mock_session)
        assert isinstance(service, ContactsService)
