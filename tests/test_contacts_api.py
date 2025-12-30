"""Tests for contacts/CRM API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_list_contacts(client: AsyncClient, auth_headers: dict):
    """Test listing contacts."""
    response = await client.get(
        "/api/v1/contacts",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "contacts" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.asyncio
async def test_list_contacts_with_search(client: AsyncClient, auth_headers: dict):
    """Test listing contacts with search query."""
    response = await client.get(
        "/api/v1/contacts?query=john",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "contacts" in data


@pytest.mark.asyncio
async def test_list_contacts_with_type_filter(client: AsyncClient, auth_headers: dict):
    """Test listing contacts filtered by type."""
    response = await client.get(
        "/api/v1/contacts?contact_type=buyer",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "contacts" in data


@pytest.mark.asyncio
async def test_create_contact(client: AsyncClient, auth_headers: dict):
    """Test creating a new contact."""
    response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "John Test",
            "email": f"john.test.{uuid4().hex[:8]}@example.com",
            "phone": "555-123-4567",
            "contact_type": "buyer",
            "company": "Test Company",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "John Test"
    assert data["contact_type"] == "buyer"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_contact_minimal(client: AsyncClient, auth_headers: dict):
    """Test creating contact with minimal fields."""
    response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "Jane Minimal",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Jane Minimal"
    assert data["contact_type"] == "other"  # Default


@pytest.mark.asyncio
async def test_create_contact_with_tags(client: AsyncClient, auth_headers: dict):
    """Test creating contact with tags."""
    response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "Tagged Contact",
            "tags": ["vip", "repeat_client"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "vip" in data["tags"]
    assert "repeat_client" in data["tags"]


@pytest.mark.asyncio
async def test_get_contact(client: AsyncClient, auth_headers: dict):
    """Test getting a specific contact."""
    # First create a contact
    create_response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "Get Test",
            "email": f"get.test.{uuid4().hex[:8]}@example.com",
        },
    )

    contact_id = create_response.json()["id"]

    # Then get it
    response = await client.get(
        f"/api/v1/contacts/{contact_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == contact_id
    assert data["full_name"] == "Get Test"


@pytest.mark.asyncio
async def test_get_contact_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting non-existent contact returns 404."""
    response = await client.get(
        f"/api/v1/contacts/{uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_contact(client: AsyncClient, auth_headers: dict):
    """Test updating a contact."""
    # First create a contact
    create_response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "Update Test",
            "email": f"update.test.{uuid4().hex[:8]}@example.com",
        },
    )

    contact_id = create_response.json()["id"]

    # Then update it
    response = await client.patch(
        f"/api/v1/contacts/{contact_id}",
        headers=auth_headers,
        json={
            "full_name": "Updated Name",
            "phone": "555-999-8888",
            "contact_type": "seller",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["phone"] == "555-999-8888"
    assert data["contact_type"] == "seller"


@pytest.mark.asyncio
async def test_add_tag_to_contact(client: AsyncClient, auth_headers: dict):
    """Test adding a tag to a contact."""
    # First create a contact
    create_response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "Tag Test",
        },
    )

    contact_id = create_response.json()["id"]

    # Add a tag
    response = await client.post(
        f"/api/v1/contacts/{contact_id}/tags/important",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "important" in data["tags"]


@pytest.mark.asyncio
async def test_remove_tag_from_contact(client: AsyncClient, auth_headers: dict):
    """Test removing a tag from a contact."""
    # First create a contact with tags
    create_response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "Remove Tag Test",
            "tags": ["keep", "remove"],
        },
    )

    contact_id = create_response.json()["id"]

    # Remove a tag
    response = await client.delete(
        f"/api/v1/contacts/{contact_id}/tags/remove",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "remove" not in data["tags"]
    assert "keep" in data["tags"]


@pytest.mark.asyncio
async def test_add_note_to_contact(client: AsyncClient, auth_headers: dict):
    """Test adding a note to a contact."""
    # First create a contact
    create_response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "Note Test",
        },
    )

    contact_id = create_response.json()["id"]

    # Add a note
    response = await client.post(
        f"/api/v1/contacts/{contact_id}/notes?note=This%20is%20a%20test%20note",
        headers=auth_headers,
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_repeat_clients(client: AsyncClient, auth_headers: dict):
    """Test getting repeat clients."""
    response = await client.get(
        "/api/v1/contacts/repeat-clients?min_transactions=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "contacts" in data
    assert "total" in data
    assert "min_transactions" in data


@pytest.mark.asyncio
async def test_get_recent_contacts(client: AsyncClient, auth_headers: dict):
    """Test getting recently updated contacts."""
    response = await client.get(
        "/api/v1/contacts/recent",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "contacts" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_contact_transactions(client: AsyncClient, auth_headers: dict):
    """Test getting transactions for a contact."""
    # First create a contact
    create_response = await client.post(
        "/api/v1/contacts",
        headers=auth_headers,
        json={
            "full_name": "Transaction Test",
            "email": f"tx.test.{uuid4().hex[:8]}@example.com",
        },
    )

    contact_id = create_response.json()["id"]

    # Get transactions
    response = await client.get(
        f"/api/v1/contacts/{contact_id}/transactions",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["contact_id"] == contact_id
    assert "transactions" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_sync_contacts_from_transaction(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test syncing contacts from transaction parties."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.post(
        f"/api/v1/contacts/sync-from-transaction/{tx_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == tx_id
    assert "synced_contacts" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_contacts_requires_auth(client: AsyncClient):
    """Test contacts endpoints require authentication."""
    response = await client.get("/api/v1/contacts")
    assert response.status_code in [401, 403]
