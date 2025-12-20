"""Document repository."""

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from packages.db.models import DocumentModel, TransactionModel
from packages.db.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[DocumentModel]):
    """Repository for document operations."""

    model = DocumentModel

    async def get_by_transaction(
        self,
        transaction_id: UUID,
        *,
        document_type: str | None = None,
        status: str | None = None,
    ) -> Sequence[DocumentModel]:
        """Get all documents for a transaction."""
        query = select(self.model).where(
            self.model.transaction_id == transaction_id
        )

        if document_type:
            query = query.where(self.model.document_type == document_type)
        if status:
            query = query.where(self.model.status == status)

        query = query.order_by(self.model.uploaded_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_pending_extraction(
        self,
        limit: int = 10,
    ) -> Sequence[DocumentModel]:
        """Get documents pending extraction."""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.status == "uploaded")
            .order_by(self.model.uploaded_at)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_needs_review(
        self,
        organization_id: UUID | None = None,
    ) -> Sequence[DocumentModel]:
        """Get documents that need human review."""
        query = (
            select(self.model)
            .join(TransactionModel, self.model.transaction_id == TransactionModel.id)
            .where(self.model.status == "needs_review")
        )

        if organization_id:
            query = query.where(TransactionModel.organization_id == organization_id)

        query = query.order_by(self.model.uploaded_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_extraction(
        self,
        document_id: UUID,
        *,
        extracted_data: dict[str, Any],
        confidence: float,
        needs_review: bool = False,
        needs_review_reason: str | None = None,
    ) -> DocumentModel | None:
        """Update document with extraction results."""
        status = "needs_review" if needs_review else "extracted"

        return await self.update(
            document_id,
            status=status,
            extracted_data=extracted_data,
            extraction_confidence=confidence,
            needs_review_reason=needs_review_reason,
        )

    async def mark_verified(
        self,
        document_id: UUID,
        verified_by: UUID,
    ) -> DocumentModel | None:
        """Mark document as verified by a user."""
        return await self.update(
            document_id,
            status="verified",
            verified_at=datetime.utcnow(),
            verified_by=verified_by,
        )

    async def mark_processing(self, document_id: UUID) -> DocumentModel | None:
        """Mark document as currently being processed."""
        return await self.update(document_id, status="processing")

    async def mark_failed(
        self,
        document_id: UUID,
        error_reason: str,
    ) -> DocumentModel | None:
        """Mark document extraction as failed."""
        return await self.update(
            document_id,
            status="needs_review",
            needs_review_reason=f"Extraction failed: {error_reason}",
        )
