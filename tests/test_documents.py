"""
Tests for document endpoints.
"""

import pytest
from io import BytesIO
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_document(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    mocker
):
    """Test uploading a document."""
    tx_id = str(test_transaction["transaction"].id)

    # Mock S3 upload
    mock_storage = mocker.patch("services.api.routers.documents.StorageService")
    mock_storage.return_value.upload_file.return_value = f"documents/{tx_id}/test.pdf"

    # Create a mock PDF file
    pdf_content = b"%PDF-1.4 test content"
    files = {"file": ("test_contract.pdf", BytesIO(pdf_content), "application/pdf")}

    response = await client.post(
        f"/api/v1/documents/upload?transaction_id={tx_id}&document_type=contract",
        headers=auth_headers,
        files=files
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_contract.pdf"
    assert data["document_type"] == "contract"
    assert data["status"] == "uploaded"
    assert data["extraction_status"] == "pending"


@pytest.mark.asyncio
async def test_upload_document_invalid_type(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict
):
    """Test uploading a document with invalid file type."""
    tx_id = str(test_transaction["transaction"].id)

    files = {"file": ("malware.exe", BytesIO(b"evil content"), "application/x-executable")}

    response = await client.post(
        f"/api/v1/documents/upload?transaction_id={tx_id}&document_type=other",
        headers=auth_headers,
        files=files
    )

    assert response.status_code == 400
    assert "file type" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_documents(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session
):
    """Test listing documents."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    # Create test documents
    doc1 = Document(
        transaction_id=tx.id,
        filename="contract.pdf",
        document_type="contract",
        storage_path=f"documents/{tx.id}/contract.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="completed",
        confidence_score=0.92,
    )
    doc2 = Document(
        transaction_id=tx.id,
        filename="addendum.pdf",
        document_type="addendum",
        storage_path=f"documents/{tx.id}/addendum.pdf",
        file_size=512,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="needs_review",
        confidence_score=0.72,
    )
    db_session.add_all([doc1, doc2])
    await db_session.commit()

    response = await client.get(
        "/api/v1/documents",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_list_documents_by_transaction(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session
):
    """Test listing documents for a specific transaction."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    doc = Document(
        transaction_id=tx.id,
        filename="inspection.pdf",
        document_type="inspection",
        storage_path=f"documents/{tx.id}/inspection.pdf",
        file_size=2048,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="completed",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/documents?transaction_id={tx.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert all(d["transaction_id"] == str(tx.id) for d in data)


@pytest.mark.asyncio
async def test_list_documents_needing_review(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session
):
    """Test listing documents that need review."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    # Create document needing review
    doc = Document(
        transaction_id=tx.id,
        filename="needs_review.pdf",
        document_type="disclosure",
        storage_path=f"documents/{tx.id}/needs_review.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="needs_review",
        confidence_score=0.65,
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.get(
        "/api/v1/documents?status=needs_review",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert all(d["extraction_status"] == "needs_review" for d in data)


@pytest.mark.asyncio
async def test_get_document(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session
):
    """Test getting a specific document."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    doc = Document(
        transaction_id=tx.id,
        filename="title.pdf",
        document_type="title",
        storage_path=f"documents/{tx.id}/title.pdf",
        file_size=3072,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="completed",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/documents/{doc.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "title.pdf"
    assert data["document_type"] == "title"


@pytest.mark.asyncio
async def test_get_extracted_data(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session
):
    """Test getting extracted data from a document."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    doc = Document(
        transaction_id=tx.id,
        filename="contract.pdf",
        document_type="contract",
        storage_path=f"documents/{tx.id}/contract.pdf",
        file_size=4096,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="completed",
        confidence_score=0.88,
        extracted_data={
            "purchase_price": 500000,
            "closing_date": "2025-03-15",
            "buyer_name": "John Doe",
            "seller_name": "Jane Smith",
            "property_address": "123 Main St, Miami, FL 33101",
        },
        flags=["Price differs from listing by 5%"],
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/documents/{doc.id}/extracted",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["extracted_data"]["purchase_price"] == 500000
    assert data["confidence_score"] == 0.88
    assert len(data["flags"]) == 1


@pytest.mark.asyncio
async def test_verify_document_approve(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session
):
    """Test approving extracted document data."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    doc = Document(
        transaction_id=tx.id,
        filename="review_me.pdf",
        document_type="contract",
        storage_path=f"documents/{tx.id}/review_me.pdf",
        file_size=2048,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="needs_review",
        confidence_score=0.72,
        extracted_data={"buyer_name": "Jon Doe"},  # Typo
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/documents/{doc.id}/verify",
        headers=auth_headers,
        json={
            "verified": True,
            "corrections": {"buyer_name": "John Doe"},  # Corrected
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_status"] == "verified"
    assert data["extracted_data"]["buyer_name"] == "John Doe"


@pytest.mark.asyncio
async def test_verify_document_reject(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session
):
    """Test rejecting and reprocessing a document."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    doc = Document(
        transaction_id=tx.id,
        filename="bad_extraction.pdf",
        document_type="contract",
        storage_path=f"documents/{tx.id}/bad_extraction.pdf",
        file_size=2048,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="needs_review",
        confidence_score=0.45,
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/documents/{doc.id}/verify",
        headers=auth_headers,
        json={"verified": False}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_status"] == "pending"  # Reset for reprocessing


@pytest.mark.asyncio
async def test_reprocess_document(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session
):
    """Test manually triggering document reprocessing."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    doc = Document(
        transaction_id=tx.id,
        filename="reprocess_me.pdf",
        document_type="contract",
        storage_path=f"documents/{tx.id}/reprocess_me.pdf",
        file_size=2048,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="failed",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/documents/{doc.id}/reprocess",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_status"] == "pending"


@pytest.mark.asyncio
async def test_delete_document(
    client: AsyncClient,
    auth_headers: dict,
    test_transaction: dict,
    db_session,
    mocker
):
    """Test deleting a document."""
    from packages.db.models import Document

    tx = test_transaction["transaction"]

    doc = Document(
        transaction_id=tx.id,
        filename="delete_me.pdf",
        document_type="other",
        storage_path=f"documents/{tx.id}/delete_me.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status="uploaded",
        extraction_status="pending",
    )
    db_session.add(doc)
    await db_session.commit()

    # Mock S3 delete
    mock_storage = mocker.patch("services.api.routers.documents.StorageService")

    response = await client.delete(
        f"/api/v1/documents/{doc.id}",
        headers=auth_headers
    )

    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(
        f"/api/v1/documents/{doc.id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404
