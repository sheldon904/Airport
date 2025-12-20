"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "New Brokerage",
            "full_name": "Jane Agent",
            "email": "jane@newbrokerage.com",
            "password": "securepassword123",
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "jane@newbrokerage.com"
    assert data["full_name"] == "Jane Agent"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_org_and_user: dict):
    """Test registration with duplicate email fails."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Another Brokerage",
            "full_name": "Another User",
            "email": test_org_and_user["user"].email,  # Duplicate email
            "password": "securepassword123",
        }
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test registration with weak password fails."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "New Brokerage",
            "full_name": "Jane Agent",
            "email": "jane@newbrokerage.com",
            "password": "weak",  # Too short
        }
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_org_and_user: dict):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_org_and_user["user"].email,
            "password": test_org_and_user["password"],
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_org_and_user: dict):
    """Test login with wrong password fails."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_org_and_user["user"].email,
            "password": "wrongpassword",
        }
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent email fails."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "anypassword",
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers: dict, test_org_and_user: dict):
    """Test getting current user info."""
    response = await client.get(
        "/api/v1/auth/me",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_org_and_user["user"].email
    assert data["full_name"] == test_org_and_user["user"].full_name


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test accessing protected endpoint without token fails."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    """Test accessing protected endpoint with invalid token fails."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_org_and_user: dict):
    """Test token refresh."""
    # First login to get tokens
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_org_and_user["user"].email,
            "password": test_org_and_user["password"],
        }
    )

    refresh_token = login_response.json()["refresh_token"]

    # Now refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, auth_headers: dict, test_org_and_user: dict):
    """Test password change."""
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": test_org_and_user["password"],
            "new_password": "newpassword456",
        }
    )

    assert response.status_code == 200

    # Verify old password no longer works
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_org_and_user["user"].email,
            "password": test_org_and_user["password"],
        }
    )
    assert login_response.status_code == 401

    # Verify new password works
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_org_and_user["user"].email,
            "password": "newpassword456",
        }
    )
    assert login_response.status_code == 200
