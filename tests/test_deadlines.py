"""
Tests for deadline endpoints.
"""

import pytest
from datetime import date, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_deadline(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test creating a new deadline."""
    tx_id = str(test_transaction["transaction"].id)
    due_date = (date.today() + timedelta(days=10)).isoformat()

    response = await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "Inspection Period Ends",
            "due_date": due_date,
            "deadline_type": "inspection",
            "is_statutory": False,
            "notes": "Schedule inspection ASAP",
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Inspection Period Ends"
    assert data["due_date"] == due_date
    assert data["status"] == "pending"
    assert data["is_statutory"] is False


@pytest.mark.asyncio
async def test_create_statutory_deadline(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test creating a statutory deadline."""
    tx_id = str(test_transaction["transaction"].id)
    due_date = (date.today() + timedelta(days=3)).isoformat()

    response = await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "FL Rescission Period",
            "due_date": due_date,
            "deadline_type": "rescission",
            "is_statutory": True,
            "statutory_reference": "FL Stat. 718.503",
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_statutory"] is True
    assert data["statutory_reference"] == "FL Stat. 718.503"


@pytest.mark.asyncio
async def test_list_deadlines(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test listing deadlines."""
    tx_id = str(test_transaction["transaction"].id)

    # Create a deadline first
    due_date = (date.today() + timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "Test Deadline",
            "due_date": due_date,
            "deadline_type": "other",
        }
    )

    response = await client.get(
        "/api/v1/deadlines",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_deadlines_by_transaction(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test listing deadlines for a specific transaction."""
    tx_id = str(test_transaction["transaction"].id)

    # Create a deadline
    due_date = (date.today() + timedelta(days=7)).isoformat()
    await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "Transaction Specific",
            "due_date": due_date,
            "deadline_type": "closing",
        }
    )

    response = await client.get(
        f"/api/v1/deadlines?transaction_id={tx_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert all(d["transaction_id"] == tx_id for d in data)


@pytest.mark.asyncio
async def test_list_upcoming_deadlines(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test listing upcoming deadlines within N days."""
    tx_id = str(test_transaction["transaction"].id)

    # Create deadline in 3 days
    soon_date = (date.today() + timedelta(days=3)).isoformat()
    await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "Soon Deadline",
            "due_date": soon_date,
            "deadline_type": "inspection",
        }
    )

    # Create deadline in 30 days
    far_date = (date.today() + timedelta(days=30)).isoformat()
    await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "Far Deadline",
            "due_date": far_date,
            "deadline_type": "closing",
        }
    )

    # Get deadlines in next 7 days
    response = await client.get(
        "/api/v1/deadlines?upcoming_days=7",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    # Should include soon deadline, not far deadline
    titles = [d["title"] for d in data]
    assert "Soon Deadline" in titles


@pytest.mark.asyncio
async def test_complete_deadline(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test completing a deadline."""
    tx_id = str(test_transaction["transaction"].id)
    due_date = (date.today() + timedelta(days=5)).isoformat()

    # Create deadline
    create_response = await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "To Complete",
            "due_date": due_date,
            "deadline_type": "other",
        }
    )
    deadline_id = create_response.json()["id"]

    # Complete it
    response = await client.post(
        f"/api/v1/deadlines/{deadline_id}/complete",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_waive_deadline(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test waiving a deadline."""
    tx_id = str(test_transaction["transaction"].id)
    due_date = (date.today() + timedelta(days=5)).isoformat()

    # Create deadline
    create_response = await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "To Waive",
            "due_date": due_date,
            "deadline_type": "inspection",
        }
    )
    deadline_id = create_response.json()["id"]

    # Waive it
    response = await client.post(
        f"/api/v1/deadlines/{deadline_id}/waive",
        headers=auth_headers,
        json={"reason": "Buyer waived inspection contingency"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "waived"
    assert "waived" in data.get("notes", "").lower() or data.get("waive_reason") is not None


@pytest.mark.asyncio
async def test_extend_deadline(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test extending a deadline."""
    tx_id = str(test_transaction["transaction"].id)
    original_date = (date.today() + timedelta(days=5)).isoformat()
    new_date = (date.today() + timedelta(days=10)).isoformat()

    # Create deadline
    create_response = await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "To Extend",
            "due_date": original_date,
            "deadline_type": "financing",
        }
    )
    deadline_id = create_response.json()["id"]

    # Extend it
    response = await client.post(
        f"/api/v1/deadlines/{deadline_id}/extend",
        headers=auth_headers,
        json={
            "new_date": new_date,
            "reason": "Lender needs more time for underwriting",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["due_date"] == new_date


@pytest.mark.asyncio
async def test_delete_deadline(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test deleting a deadline."""
    tx_id = str(test_transaction["transaction"].id)
    due_date = (date.today() + timedelta(days=5)).isoformat()

    # Create deadline
    create_response = await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "To Delete",
            "due_date": due_date,
            "deadline_type": "other",
        }
    )
    deadline_id = create_response.json()["id"]

    # Delete it
    response = await client.delete(
        f"/api/v1/deadlines/{deadline_id}",
        headers=auth_headers
    )

    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(
        f"/api/v1/deadlines/{deadline_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_complete_already_completed(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test that completing an already completed deadline fails."""
    tx_id = str(test_transaction["transaction"].id)
    due_date = (date.today() + timedelta(days=5)).isoformat()

    # Create and complete deadline
    create_response = await client.post(
        "/api/v1/deadlines",
        headers=auth_headers,
        json={
            "transaction_id": tx_id,
            "title": "Already Done",
            "due_date": due_date,
            "deadline_type": "other",
        }
    )
    deadline_id = create_response.json()["id"]

    await client.post(
        f"/api/v1/deadlines/{deadline_id}/complete",
        headers=auth_headers
    )

    # Try to complete again
    response = await client.post(
        f"/api/v1/deadlines/{deadline_id}/complete",
        headers=auth_headers
    )

    assert response.status_code == 400
