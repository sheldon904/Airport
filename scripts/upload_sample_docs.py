"""
Upload generated sample documents to transactions in the database.

This script:
1. Reads transactions from the database
2. Matches them with generated documents
3. Uploads documents to MinIO storage
4. Creates document records in the database

Run with: python scripts/upload_sample_docs.py
"""

import asyncio
from pathlib import Path
from datetime import datetime
from uuid import UUID, uuid4
import mimetypes

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Initialize mimetypes
mimetypes.init()

# Database configuration
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/airport"

# MinIO configuration
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET = "airport-documents"

# Document directory
DOCS_DIR = Path(__file__).parent.parent / "sample_documents"


async def upload_documents():
    """Upload sample documents to transactions."""
    # Import models here to avoid circular imports
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from packages.db.models import TransactionModel, DocumentModel, OrganizationModel

    # Create database engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Initialize MinIO client
    from minio import Minio
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    # Mapping from document filename prefix to transaction address keywords
    doc_to_transaction = {
        "brickell_condo": "1842 Brickell",
        "coconut_grove": "3456 Coconut Grove",
        "tampa_downtown": "401 E Jackson",
        "coral_gables": "742 Alhambra",
        "naples_bay": "8901 Bay Colony",
    }

    # Document type mapping
    filename_to_doctype = {
        "contract_": "purchase_agreement",
        "closing_disclosure_": "closing_disclosure",
        "lead_disclosure_": "lead_paint_disclosure",
        "sellers_disclosure_": "sellers_disclosure",
        "hoa_disclosure_": "hoa_disclosure",
        "inspection_report_": "inspection_report",
        "title_commitment_": "title_commitment",
    }

    print("=" * 70)
    print("UPLOADING SAMPLE DOCUMENTS TO TRANSACTIONS")
    print("=" * 70)

    async with async_session() as session:
        # Get all transactions
        result = await session.execute(select(TransactionModel))
        transactions = result.scalars().all()

        print(f"\nFound {len(transactions)} transactions in database")

        # Get organization for uploaded_by
        org_result = await session.execute(select(OrganizationModel).limit(1))
        org = org_result.scalar_one_or_none()

        if not org:
            print("ERROR: No organization found in database!")
            return

        # Get first user from org for uploaded_by
        from packages.db.models import UserModel
        user_result = await session.execute(
            select(UserModel).where(UserModel.organization_id == org.id).limit(1)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            print("ERROR: No user found in database!")
            return

        uploaded_count = 0

        # Process each PDF in the sample documents directory
        for pdf_file in sorted(DOCS_DIR.glob("*.pdf")):
            # Find which transaction this document belongs to
            doc_key = None
            for key in doc_to_transaction:
                if key in pdf_file.name:
                    doc_key = key
                    break

            if not doc_key:
                print(f"  SKIP: {pdf_file.name} - no matching transaction key")
                continue

            # Find the transaction by address keyword
            address_keyword = doc_to_transaction[doc_key]
            matching_tx = None
            for tx in transactions:
                # property_address is a JSONB dict with street, city, etc.
                street = tx.property_address.get("street", "") if tx.property_address else ""
                if address_keyword.lower() in street.lower():
                    matching_tx = tx
                    break

            if not matching_tx:
                print(f"  SKIP: {pdf_file.name} - no matching transaction for '{address_keyword}'")
                continue

            # Determine document type
            doc_type = "other"
            for prefix, dtype in filename_to_doctype.items():
                if pdf_file.name.startswith(prefix):
                    doc_type = dtype
                    break

            # Check if document already exists
            existing_result = await session.execute(
                select(DocumentModel).where(
                    DocumentModel.transaction_id == matching_tx.id,
                    DocumentModel.filename == pdf_file.name,
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                tx_street = matching_tx.property_address.get("street", "")[:30] if matching_tx.property_address else "Unknown"
                print(f"  EXISTS: {pdf_file.name} already uploaded to {tx_street}...")
                continue

            # Read file content
            file_content = pdf_file.read_bytes()
            file_size = len(file_content)

            # Create storage path
            storage_path = f"{org.id}/{matching_tx.id}/{pdf_file.name}"

            # Upload to MinIO
            try:
                from io import BytesIO
                minio_client.put_object(
                    MINIO_BUCKET,
                    storage_path,
                    BytesIO(file_content),
                    file_size,
                    content_type="application/pdf",
                )
            except Exception as e:
                print(f"  ERROR: Failed to upload {pdf_file.name} to MinIO: {e}")
                continue

            # Create document record (organization_id is derived from transaction)
            document = DocumentModel(
                id=uuid4(),
                transaction_id=matching_tx.id,
                uploaded_by=user.id,
                document_type=doc_type,
                filename=pdf_file.name,
                storage_path=storage_path,
                content_type="application/pdf",
                file_size=file_size,
                status="uploaded",  # Ready for AI extraction
                uploaded_at=datetime.utcnow(),
            )

            session.add(document)
            uploaded_count += 1

            tx_addr = matching_tx.property_address.get("street", "Unknown")[:40] if matching_tx.property_address else "Unknown"
            print(f"  UPLOADED: {pdf_file.name}")
            print(f"           -> Transaction: {tx_addr}...")
            print(f"           -> Type: {doc_type}")

        # Commit all changes
        await session.commit()

        print()
        print("=" * 70)
        print(f"UPLOAD COMPLETE: {uploaded_count} documents uploaded")
        print("=" * 70)
        print()
        print("Documents are now ready for AI extraction.")
        print("The DocumentExtractAgent will process them when triggered.")


if __name__ == "__main__":
    asyncio.run(upload_documents())
