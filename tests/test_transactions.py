"""
Tests for transaction endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_transaction(client: AsyncClient, auth_headers: dict):
    """Test creating a new transaction."""
    response = await client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json={
            "property_address": {
                "street": "456 Oak Lane",
                "city": "Tampa",
                "state": "FL",
                "zip_code": "33602"
            },
            "transaction_type": "purchase",
            "purchase_price": 350000,
            "closing_date": "2025-03-01",
            "buyer_name": "Alice Buyer",
            "seller_name": "Bob Seller",
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["property_address"]["street"] == "456 Oak Lane"
    assert data["property_address"]["city"] == "Tampa"
    assert data["transaction_type"] == "purchase"
    assert data["purchase_price"] == 350000
    assert data["status"] == "pending"
    assert "id" in data
    assert "checklist" in data  # FL checklist should be initialized


@pytest.mark.asyncio
async def test_create_transaction_minimal(client: AsyncClient, auth_headers: dict):
    """Test creating a transaction with minimal fields."""
    response = await client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json={
            "property_address": {
                "street": "789 Pine St",
                "city": "Orlando",
                "state": "FL",
                "zip_code": "32801"
            },
            "transaction_type": "sale",
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["transaction_type"] == "sale"
    assert data["purchase_price"] is None
    assert data["closing_date"] is None


@pytest.mark.asyncio
async def test_create_transaction_unauthorized(client: AsyncClient):
    """Test creating transaction without auth fails."""
    response = await client.post(
        "/api/v1/transactions",
        json={
            "property_address": {
                "street": "456 Oak Lane",
                "city": "Tampa",
                "state": "FL",
                "zip_code": "33602"
            },
            "transaction_type": "purchase",
        }
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_transactions(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test listing transactions."""
    response = await client.get(
        "/api/v1/transactions",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["property_address"]["street"] == "123 Test St"


@pytest.mark.asyncio
async def test_list_transactions_with_status_filter(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test listing transactions with status filter."""
    response = await client.get(
        "/api/v1/transactions?status=under_contract",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert all(tx["status"] == "under_contract" for tx in data)


@pytest.mark.asyncio
async def test_get_transaction(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test getting a specific transaction."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.get(
        f"/api/v1/transactions/{tx_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tx_id
    assert data["property_address"]["city"] == "Miami"


@pytest.mark.asyncio
async def test_get_transaction_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting non-existent transaction returns 404."""
    from uuid import uuid4

    response = await client.get(
        f"/api/v1/transactions/{uuid4()}",
        headers=auth_headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_transaction(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test updating a transaction."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.patch(
        f"/api/v1/transactions/{tx_id}",
        headers=auth_headers,
        json={
            "status": "inspection",
            "purchase_price": 525000,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inspection"
    assert data["purchase_price"] == 525000


@pytest.mark.asyncio
async def test_update_transaction_checklist(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test updating transaction checklist."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.patch(
        f"/api/v1/transactions/{tx_id}",
        headers=auth_headers,
        json={
            "checklist": {
                "contract_received": True,
                "earnest_money_deposited": True,
                "inspection_ordered": True,
                "title_ordered": False,
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["checklist"]["earnest_money_deposited"] is True
    assert data["checklist"]["inspection_ordered"] is True


@pytest.mark.asyncio
async def test_delete_transaction(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test deleting a transaction."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.delete(
        f"/api/v1/transactions/{tx_id}",
        headers=auth_headers
    )

    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(
        f"/api/v1/transactions/{tx_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_dashboard(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test getting dashboard stats."""
    response = await client.get(
        "/api/v1/transactions/dashboard",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "active_transactions" in data
    assert "pending_deadlines" in data
    assert "documents_needing_review" in data
    assert "completed_this_month" in data
    assert "total_volume" in data
    assert data["active_transactions"] >= 1


@pytest.mark.asyncio
async def test_transaction_isolation(
    client: AsyncClient,
    db_session,
    test_org_and_user: dict
):
    """Test that users can only see their organization's transactions."""
    from packages.db.models import Organization, User, Transaction
    from packages.core.services.auth import AuthService

    auth_service = AuthService()

    # Create another organization and user
    org2 = Organization(name="Other Brokerage", settings={})
    db_session.add(org2)
    await db_session.flush()

    user2 = User(
        organization_id=org2.id,
        email="other@example.com",
        password_hash=auth_service.hash_password("password123"),
        full_name="Other User",
        role="admin",
    )
    db_session.add(user2)

    # Create transaction for org2
    tx2 = Transaction(
        organization_id=org2.id,
        created_by_id=user2.id,
        property_address={"street": "999 Other St", "city": "Miami", "state": "FL", "zip_code": "33101"},
        transaction_type="purchase",
        status="pending",
    )
    db_session.add(tx2)
    await db_session.commit()

    # Login as user2
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "password123"}
    )
    user2_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # User2 should only see their transaction
    response = await client.get(
        "/api/v1/transactions",
        headers=user2_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["property_address"]["street"] == "999 Other St"
