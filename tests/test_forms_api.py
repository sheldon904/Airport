"""Tests for forms API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_list_form_templates(client: AsyncClient, auth_headers: dict):
    """Test listing form templates."""
    response = await client.get(
        "/api/v1/forms/templates",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "forms" in data
    assert "total" in data
    assert data["total"] > 0


@pytest.mark.asyncio
async def test_list_form_templates_by_category(client: AsyncClient, auth_headers: dict):
    """Test listing form templates filtered by category."""
    response = await client.get(
        "/api/v1/forms/templates?category=disclosure",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "forms" in data
    assert all(f["category"] == "disclosure" for f in data["forms"])


@pytest.mark.asyncio
async def test_list_form_templates_invalid_category(client: AsyncClient, auth_headers: dict):
    """Test listing form templates with invalid category returns error."""
    response = await client.get(
        "/api/v1/forms/templates?category=invalid_category",
        headers=auth_headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_form_template(client: AsyncClient, auth_headers: dict):
    """Test getting a specific form template."""
    response = await client.get(
        "/api/v1/forms/templates/far_bar_as_is",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "far_bar_as_is"
    assert "name" in data
    assert "fields" in data
    assert len(data["fields"]) > 0


@pytest.mark.asyncio
async def test_get_form_template_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting non-existent form template returns 404."""
    response = await client.get(
        "/api/v1/forms/templates/nonexistent_form",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_populate_form(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test populating a form with transaction data."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.post(
        "/api/v1/forms/populate/far_bar_as_is",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "include_extracted_data": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == "far_bar_as_is"
    assert "populated_fields" in data
    assert "missing_required" in data
    assert "is_complete" in data


@pytest.mark.asyncio
async def test_populate_form_transaction_not_found(client: AsyncClient, auth_headers: dict):
    """Test populating form with non-existent transaction."""
    response = await client.post(
        "/api/v1/forms/populate/far_bar_as_is",
        headers=auth_headers,
        json={
            "transaction_id": str(uuid4()),
            "include_extracted_data": True,
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_populate_form_template_not_found(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test populating non-existent form template."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.post(
        "/api/v1/forms/populate/nonexistent_form",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_required_forms(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test getting required forms for a transaction."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.get(
        f"/api/v1/forms/required/{tx_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == tx_id
    assert "required_forms" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_disclosure_requirements(client: AsyncClient, auth_headers: dict, test_transaction: dict):
    """Test getting disclosure requirements for a transaction."""
    tx_id = str(test_transaction["transaction"].id)

    response = await client.get(
        f"/api/v1/forms/disclosures/{tx_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == tx_id
    assert "disclosures" in data
    assert "total_required" in data


@pytest.mark.asyncio
async def test_populate_all_required_forms(client: AsyncClient, auth_headers: dict, test_transaction: dict):
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


@pytest.mark.asyncio
async def test_forms_requires_auth(client: AsyncClient):
    """Test forms endpoints require authentication."""
    response = await client.get("/api/v1/forms/templates")
    assert response.status_code in [401, 403]
