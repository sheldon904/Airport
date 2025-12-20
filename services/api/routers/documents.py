"""Document management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db import get_db

router = APIRouter()


# === Request/Response Models ===


class DocumentResponse(BaseModel):
    """Document response model."""

    id: UUID
    transaction_id: UUID
    document_type: str
    filename: str
    status: str
    extraction_confidence: float | None
    needs_review: bool
    uploaded_at: str


class ExtractedDataResponse(BaseModel):
    """Extracted data from a document."""

    document_id: UUID
    parties: list[dict[str, str]]
    dates: dict[str, str]
    financial: dict[str, float]
    contingencies: list[dict[str, str]]
    confidence: float
    needs_review_items: list[str]


# === Endpoints ===


@router.post("/upload/{transaction_id}", status_code=status.HTTP_201_CREATED)
async def upload_document(
    transaction_id: UUID,
    file: UploadFile = File(...),
    document_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Upload a document to a transaction.

    The document will be stored and queued for AI extraction.
    Document type will be auto-detected if not specified.

    Triggers:
    - DocumentExtractAgent for data extraction
    - ChecklistAgent for checklist updates
    """
    # TODO: Implement document upload
    # 1. Validate transaction exists and user has access
    # 2. Store file in S3
    # 3. Create document record
    # 4. Queue extraction job
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document upload not yet implemented",
    )


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get document metadata and status."""
    # TODO: Implement document retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document retrieval not yet implemented",
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Download the original document file.

    Returns a presigned URL for direct S3 download.
    """
    # TODO: Implement document download
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document download not yet implemented",
    )


@router.get("/{document_id}/extracted")
async def get_extracted_data(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ExtractedDataResponse:
    """
    Get the AI-extracted data from a document.

    Returns structured data parsed from the document along
    with confidence scores and items requiring review.
    """
    # TODO: Implement extracted data retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Extracted data retrieval not yet implemented",
    )


@router.post("/{document_id}/verify")
async def verify_extracted_data(
    document_id: UUID,
    corrections: dict[str, str] | None = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Verify or correct AI-extracted data.

    Human-in-the-loop confirmation of extracted data.
    Any corrections provided will update the stored data.

    Triggers:
    - DeadlineAgent if dates were confirmed/corrected
    - ChecklistAgent for document status update
    """
    # TODO: Implement verification
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Verification not yet implemented",
    )


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Re-run AI extraction on a document.

    Useful if extraction failed or new extraction capabilities
    are available.
    """
    # TODO: Implement reprocessing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Reprocessing not yet implemented",
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document from a transaction."""
    # TODO: Implement document deletion
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document deletion not yet implemented",
    )
