"""Document service - business logic for document management."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import DocumentType, DocumentStatus
from packages.db.repositories.document import DocumentRepository
from packages.db.repositories.transaction import TransactionRepository
from packages.db.repositories.job_queue import JobQueueRepository
from packages.db.models import DocumentModel


class DocumentService:
    """
    Service for document business logic.

    Handles:
    - Document upload and storage
    - Extraction job queuing
    - Verification workflow
    - Checklist updates
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.document_repo = DocumentRepository(session)
        self.transaction_repo = TransactionRepository(session)
        self.job_queue = JobQueueRepository(session)

    async def upload_document(
        self,
        *,
        transaction_id: UUID,
        organization_id: UUID,
        uploaded_by: UUID,
        filename: str,
        storage_path: str,
        content_type: str,
        file_size: int,
        document_type: str | None = None,
    ) -> DocumentModel:
        """
        Record a document upload and queue for extraction.

        The actual file storage is handled by the storage service.
        This method records the metadata and queues the extraction job.
        """
        # Verify transaction access
        transaction = await self.transaction_repo.get_by_id(transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            raise ValueError("Transaction not found or access denied")

        # Auto-detect document type if not provided
        if not document_type:
            document_type = self._detect_document_type(filename)

        # Create document record
        document = await self.document_repo.create(
            id=uuid4(),
            transaction_id=transaction_id,
            uploaded_by=uploaded_by,
            document_type=document_type,
            filename=filename,
            storage_path=storage_path,
            content_type=content_type,
            file_size=file_size,
            status=DocumentStatus.UPLOADED,
        )

        # Queue extraction job
        await self.job_queue.enqueue(
            job_type="document_extraction",
            payload={
                "document_id": str(document.id),
                "transaction_id": str(transaction_id),
                "organization_id": str(organization_id),
                "document_type": document_type,
                "storage_path": storage_path,
                "filename": filename,
            },
            priority=1,  # Higher priority than reminders
        )

        return document

    def _detect_document_type(self, filename: str) -> str:
        """Attempt to detect document type from filename."""
        filename_lower = filename.lower()

        type_patterns = {
            DocumentType.PURCHASE_CONTRACT: [
                "contract", "purchase", "agreement", "far-bar", "farbar"
            ],
            DocumentType.AMENDMENT: ["amendment", "amend"],
            DocumentType.ADDENDUM: ["addendum", "add"],
            DocumentType.SELLER_DISCLOSURE: ["seller", "disclosure", "spd"],
            DocumentType.LEAD_PAINT: ["lead", "paint", "lbp"],
            DocumentType.HOA_DISCLOSURE: ["hoa", "association", "condo"],
            DocumentType.INSPECTION_REPORT: ["inspection", "inspect"],
            DocumentType.APPRAISAL: ["appraisal", "appraiser"],
            DocumentType.TITLE_COMMITMENT: ["title", "commitment"],
            DocumentType.CLOSING_DISCLOSURE: ["closing", "cd", "settlement"],
            DocumentType.PRE_APPROVAL: ["preapproval", "pre-approval", "approval"],
        }

        for doc_type, patterns in type_patterns.items():
            for pattern in patterns:
                if pattern in filename_lower:
                    return doc_type.value

        return DocumentType.OTHER.value

    async def get_document(
        self,
        document_id: UUID,
        organization_id: UUID,
    ) -> DocumentModel | None:
        """Get document with access control."""
        document = await self.document_repo.get_by_id(document_id)
        if not document:
            return None

        # Verify access through transaction
        transaction = await self.transaction_repo.get_by_id(document.transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return None

        return document

    async def get_transaction_documents(
        self,
        transaction_id: UUID,
        organization_id: UUID,
        *,
        document_type: str | None = None,
        status: str | None = None,
    ) -> list[DocumentModel]:
        """Get all documents for a transaction."""
        # Verify access
        transaction = await self.transaction_repo.get_by_id(transaction_id)
        if not transaction or transaction.organization_id != organization_id:
            return []

        docs = await self.document_repo.get_by_transaction(
            transaction_id,
            document_type=document_type,
            status=status,
        )
        return list(docs)

    async def record_extraction_result(
        self,
        document_id: UUID,
        *,
        extracted_data: dict[str, Any],
        confidence: float,
        needs_review: bool,
        needs_review_reason: str | None = None,
    ) -> DocumentModel | None:
        """Record extraction results from agent."""
        return await self.document_repo.update_extraction(
            document_id,
            extracted_data=extracted_data,
            confidence=confidence,
            needs_review=needs_review,
            needs_review_reason=needs_review_reason,
        )

    async def verify_document(
        self,
        document_id: UUID,
        organization_id: UUID,
        verified_by: UUID,
        corrections: dict[str, Any] | None = None,
    ) -> DocumentModel | None:
        """
        Verify document extraction with optional corrections.

        Human-in-the-loop confirmation of AI-extracted data.
        """
        document = await self.get_document(document_id, organization_id)
        if not document:
            return None

        # Apply corrections if provided
        if corrections and document.extracted_data:
            merged_data = {**document.extracted_data, **corrections}
            await self.document_repo.update(
                document_id,
                extracted_data=merged_data,
            )

        # Mark as verified
        return await self.document_repo.mark_verified(document_id, verified_by)

    async def reprocess_document(
        self,
        document_id: UUID,
        organization_id: UUID,
    ) -> DocumentModel | None:
        """Queue document for re-extraction."""
        document = await self.get_document(document_id, organization_id)
        if not document:
            return None

        # Reset status
        await self.document_repo.update(
            document_id,
            status=DocumentStatus.UPLOADED,
            extracted_data=None,
            extraction_confidence=None,
            needs_review_reason=None,
        )

        # Queue new extraction job
        await self.job_queue.enqueue(
            job_type="document_extraction",
            payload={
                "document_id": str(document.id),
                "transaction_id": str(document.transaction_id),
                "document_type": document.document_type,
                "storage_path": document.storage_path,
                "filename": document.filename,
                "reprocess": True,
            },
            priority=0,
        )

        return await self.document_repo.get_by_id(document_id)

    async def delete_document(
        self,
        document_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Delete a document from database.

        Note: Storage cleanup is handled by the API router which has
        access to the storage service.
        """
        document = await self.get_document(document_id, organization_id)
        if not document:
            return False

        return await self.document_repo.delete(document_id)

    async def get_review_queue(
        self,
        organization_id: UUID,
    ) -> list[DocumentModel]:
        """Get documents needing human review for an organization."""
        docs = await self.document_repo.get_needs_review(organization_id)
        return list(docs)
