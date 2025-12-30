"""Integration tests for cross-service workflows."""

import pytest
from datetime import date, timedelta
from uuid import uuid4
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDocumentToFormWorkflow:
    """Test workflow from document extraction to form population."""

    async def test_extracted_data_populates_forms(
        self, client: AsyncClient, auth_headers: dict, test_transaction: dict
    ):
        """Test that extracted document data is used in form population."""
        tx_id = str(test_transaction["transaction"].id)

        # Get required forms for the transaction
        forms_response = await client.get(
            f"/api/v1/forms/required/{tx_id}",
            headers=auth_headers,
        )

        assert forms_response.status_code == 200
        required_forms = forms_response.json()
        assert "required_forms" in required_forms

        # Populate a form and check data comes through
        populate_response = await client.post(
            "/api/v1/forms/populate/far_bar_as_is",
            headers=auth_headers,
            json={
                "transaction_id": tx_id,
                "include_extracted_data": True,
            },
        )

        assert populate_response.status_code == 200
        form_data = populate_response.json()
        assert "populated_fields" in form_data
        assert "missing_required" in form_data


@pytest.mark.asyncio
class TestPortalAccessWorkflow:
    """Test external party portal access workflow."""

    async def test_generate_and_validate_portal_token(
        self, client: AsyncClient, auth_headers: dict, test_transaction: dict
    ):
        """Test generating and validating a portal access token."""
        tx_id = str(test_transaction["transaction"].id)

        # Generate token
        gen_response = await client.post(
            "/api/v1/portal/generate-token",
            headers=auth_headers,
            json={
                "transaction_id": tx_id,
                "party_email": "external@example.com",
                "party_role": "buyer",
                "expires_hours": 24,
            },
        )

        assert gen_response.status_code == 200
        token_data = gen_response.json()
        assert "token" in token_data
        assert "expires_at" in token_data

        token = token_data["token"]

        # Validate the token
        validate_response = await client.post(
            f"/api/v1/portal/validate-token?token={token}",
        )

        assert validate_response.status_code == 200
        validation = validate_response.json()
        assert validation["valid"] is True
        assert validation["party_email"] == "external@example.com"
        assert validation["party_role"] == "buyer"

    async def test_portal_view_returns_filtered_data(
        self, client: AsyncClient, auth_headers: dict, test_transaction: dict
    ):
        """Test that portal view returns appropriately filtered transaction data."""
        tx_id = str(test_transaction["transaction"].id)

        # Generate token for buyer
        gen_response = await client.post(
            "/api/v1/portal/generate-token",
            headers=auth_headers,
            json={
                "transaction_id": tx_id,
                "party_email": "buyer@example.com",
                "party_role": "buyer",
            },
        )

        token = gen_response.json()["token"]

        # Access portal view
        view_response = await client.get(
            f"/api/v1/portal/view?token={token}",
        )

        assert view_response.status_code == 200
        portal_data = view_response.json()

        # Should have transaction info
        assert portal_data["transaction_id"] == tx_id
        assert "status" in portal_data
        assert "deadlines" in portal_data
        assert "documents" in portal_data

    async def test_portal_token_management(
        self, client: AsyncClient, auth_headers: dict, test_transaction: dict
    ):
        """Test listing and revoking portal tokens."""
        tx_id = str(test_transaction["transaction"].id)

        # Generate a token
        await client.post(
            "/api/v1/portal/generate-token",
            headers=auth_headers,
            json={
                "transaction_id": tx_id,
                "party_email": "party1@example.com",
                "party_role": "seller",
            },
        )

        # List tokens
        list_response = await client.get(
            f"/api/v1/portal/tokens/{tx_id}",
            headers=auth_headers,
        )

        assert list_response.status_code == 200
        tokens = list_response.json()
        assert "tokens" in tokens

        # Revoke token
        revoke_response = await client.delete(
            f"/api/v1/portal/tokens/{tx_id}/party1@example.com",
            headers=auth_headers,
        )

        assert revoke_response.status_code == 200
        assert revoke_response.json()["status"] == "revoked"


@pytest.mark.asyncio
class TestContactsCRMWorkflow:
    """Test contacts/CRM workflows."""

    async def test_contact_lifecycle(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test full contact lifecycle: create, update, tag, note."""
        # Create contact
        unique_email = f"lifecycle.{uuid4().hex[:8]}@example.com"
        create_response = await client.post(
            "/api/v1/contacts",
            headers=auth_headers,
            json={
                "full_name": "Lifecycle Test",
                "email": unique_email,
                "contact_type": "buyer",
            },
        )

        assert create_response.status_code == 200
        contact = create_response.json()
        contact_id = contact["id"]

        # Update contact
        update_response = await client.patch(
            f"/api/v1/contacts/{contact_id}",
            headers=auth_headers,
            json={
                "phone": "555-111-2222",
                "company": "Test Company",
            },
        )

        assert update_response.status_code == 200
        assert update_response.json()["phone"] == "555-111-2222"

        # Add tag
        tag_response = await client.post(
            f"/api/v1/contacts/{contact_id}/tags/vip",
            headers=auth_headers,
        )

        assert tag_response.status_code == 200
        assert "vip" in tag_response.json()["tags"]

        # Add note
        note_response = await client.post(
            f"/api/v1/contacts/{contact_id}/notes?note=Important%20client",
            headers=auth_headers,
        )

        assert note_response.status_code == 200

        # Verify contact has all updates
        get_response = await client.get(
            f"/api/v1/contacts/{contact_id}",
            headers=auth_headers,
        )

        assert get_response.status_code == 200
        final_contact = get_response.json()
        assert final_contact["phone"] == "555-111-2222"
        assert "vip" in final_contact["tags"]

    async def test_sync_contacts_from_transaction(
        self, client: AsyncClient, auth_headers: dict, test_transaction: dict
    ):
        """Test syncing contacts from transaction parties."""
        tx_id = str(test_transaction["transaction"].id)

        sync_response = await client.post(
            f"/api/v1/contacts/sync-from-transaction/{tx_id}",
            headers=auth_headers,
        )

        assert sync_response.status_code == 200
        sync_data = sync_response.json()
        assert sync_data["transaction_id"] == tx_id
        assert "synced_contacts" in sync_data
        assert "total" in sync_data


@pytest.mark.asyncio
class TestDisclosureWorkflow:
    """Test Florida disclosure requirements workflow."""

    async def test_disclosure_checklist_for_transaction(
        self, client: AsyncClient, auth_headers: dict, test_transaction: dict
    ):
        """Test getting disclosure checklist for a transaction."""
        tx_id = str(test_transaction["transaction"].id)

        response = await client.get(
            f"/api/v1/forms/disclosures/{tx_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        disclosures = response.json()
        assert disclosures["transaction_id"] == tx_id
        assert "disclosures" in disclosures
        assert "total_required" in disclosures

        # Radon disclosure should always be required in Florida
        disclosure_ids = [d["id"] for d in disclosures["disclosures"] if d["required"]]
        assert "radon_gas" in disclosure_ids


@pytest.mark.asyncio
class TestFormPopulationWorkflow:
    """Test form population workflow."""

    async def test_populate_all_required_forms(
        self, client: AsyncClient, auth_headers: dict, test_transaction: dict
    ):
        """Test populating all required forms for a transaction."""
        tx_id = str(test_transaction["transaction"].id)

        response = await client.post(
            f"/api/v1/forms/populate-all/{tx_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transaction_id"] == tx_id
        assert "forms" in data
        assert "total" in data
        assert "complete" in data
        assert "incomplete" in data

    async def test_form_template_listing_and_filtering(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing form templates with category filtering."""
        # List all templates
        all_response = await client.get(
            "/api/v1/forms/templates",
            headers=auth_headers,
        )

        assert all_response.status_code == 200
        all_templates = all_response.json()
        assert all_templates["total"] > 0

        # Filter by disclosure category
        disclosure_response = await client.get(
            "/api/v1/forms/templates?category=disclosure",
            headers=auth_headers,
        )

        assert disclosure_response.status_code == 200
        disclosure_templates = disclosure_response.json()
        assert all(t["category"] == "disclosure" for t in disclosure_templates["forms"])


@pytest.mark.asyncio
class TestAuthenticationWorkflow:
    """Test authentication-related workflows."""

    async def test_unauthenticated_access_blocked(self, client: AsyncClient):
        """Test that endpoints require authentication."""
        protected_endpoints = [
            ("/api/v1/contacts", "GET"),
            ("/api/v1/forms/templates", "GET"),
            ("/api/v1/portal/generate-token", "POST"),
        ]

        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})

            assert response.status_code in [401, 403, 422], \
                f"Expected 401/403/422 for {method} {endpoint}, got {response.status_code}"

    async def test_invalid_portal_token_rejected(self, client: AsyncClient):
        """Test that invalid portal tokens are rejected."""
        response = await client.get(
            "/api/v1/portal/view?token=invalid.fake.token",
        )

        assert response.status_code == 401
