"""Tests for portal API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_generate_portal_token(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test generating a portal access token."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.post(
        "/api/v1/portal/generate-token",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "party_email": "buyer@example.com",
            "party_role": "buyer",
            "expires_hours": 72,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "expires_at" in data
    assert "portal_url" in data
    assert len(data["token"]) > 0


@pytest.mark.asyncio
async def test_generate_portal_token_invalid_role(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test generating token with invalid role fails."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.post(
        "/api/v1/portal/generate-token",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "party_email": "random@example.com",
            "party_role": "random_person",
        },
    )

    # Should fail validation or return error
    assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
async def test_generate_portal_token_transaction_not_found(client: AsyncClient, auth_headers: dict):
    """Test generating token for non-existent transaction."""
    response = await client.post(
        "/api/v1/portal/generate-token",
        headers=auth_headers,
        json={
            "transaction_id": str(uuid4()),
            "party_email": "buyer@example.com",
            "party_role": "buyer",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_validate_portal_token_valid(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test validating a valid portal token."""
    tx_id = str(test_transaction["transaction"].id)

    # First generate a token
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

    # Then validate it
    response = await client.post(
        f"/api/v1/portal/validate-token?token={token}",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["party_email"] == "buyer@example.com"
    assert data["party_role"] == "buyer"


@pytest.mark.asyncio
async def test_validate_portal_token_invalid(client: AsyncClient):
    """Test validating an invalid token."""
    response = await client.post(
        "/api/v1/portal/validate-token?token=invalid.token.here",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "error" in data


@pytest.mark.asyncio
async def test_get_portal_data_valid_token(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test getting portal data with valid token."""
    tx_id = str(test_transaction["transaction"].id)

    # First generate a token
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

    # Then get portal data
    response = await client.get(
        f"/api/v1/portal/view?token={token}",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == tx_id
    assert "property_address" in data
    assert "status" in data
    assert "deadlines" in data
    assert "documents" in data


@pytest.mark.asyncio
async def test_get_portal_data_invalid_token(client: AsyncClient):
    """Test getting portal data with invalid token."""
    response = await client.get(
        "/api/v1/portal/view?token=invalid.token.here",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_portal_tokens(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test listing portal tokens for a transaction."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.get(
        f"/api/v1/portal/tokens/{tx_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == tx_id
    assert "tokens" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_revoke_portal_token(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test revoking a portal token."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.delete(
        f"/api/v1/portal/tokens/{tx_id}/buyer@example.com",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "revoked"


@pytest.mark.asyncio
async def test_portal_generate_requires_auth(client: AsyncClient):
    """Test portal generate endpoint requires authentication."""
    response = await client.post(
        "/api/v1/portal/generate-token",
        json={
            "transaction_id": str(uuid4()),
            "party_email": "test@example.com",
            "party_role": "buyer",
        },
    )

    assert response.status_code in [401, 403]
