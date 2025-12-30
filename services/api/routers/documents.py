"""Document management endpoints with proper error handling and security."""

import magic
from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
import structlog

from services.api.dependencies import (
    CurrentUserDep,
    DocumentServiceDep,
    StorageDep,
)
from packages.core.exceptions import StorageError

router = APIRouter()
logger = structlog.get_logger()


# === Request/Response Models ===


class DocumentResponse(BaseModel):
    """Document response model."""

    id: UUID
    transaction_id: UUID
    document_type: str
    filename: str
    content_type: str
    file_size: int | None
    status: str
    extraction_status: str  # Maps from status for frontend compatibility
    extraction_confidence: float | None
    confidence_score: float | None  # Alias for extraction_confidence
    needs_review: bool
    needs_review_reason: str | None
    uploaded_at: str
    created_at: str  # Alias for uploaded_at for frontend compatibility
    verified_at: str | None
    flags: list[str]  # Derived from extracted_data unclear_items


class ExtractedDataResponse(BaseModel):
    """Extracted data from a document."""

    document_id: UUID
    document_type: str
    extracted_data: dict[str, Any]
    confidence: float | None
    needs_review_items: list[str]


class VerifyDocumentRequest(BaseModel):
    """Request to verify document extraction."""

    corrections: dict[str, Any] | None = None


class PresignedUrlResponse(BaseModel):
    """Presigned URL response."""

    url: str
    expires_in: int


class UploadUrlResponse(BaseModel):
    """Upload URL response for direct upload."""

    upload_url: str
    storage_path: str
    expires_in: int


# === Constants ===

# Allowed MIME types and their file signatures
ALLOWED_TYPES = {
    "application/pdf": {
        "magic_bytes": [b"%PDF"],
        "extensions": [".pdf"],
    },
    "image/jpeg": {
        "magic_bytes": [b"\xff\xd8\xff"],
        "extensions": [".jpg", ".jpeg"],
    },
    "image/png": {
        "magic_bytes": [b"\x89PNG\r\n\x1a\n"],
        "extensions": [".png"],
    },
    "image/tiff": {
        "magic_bytes": [b"II*\x00", b"MM\x00*"],
        "extensions": [".tiff", ".tif"],
    },
    "image/webp": {
        "magic_bytes": [b"RIFF"],  # WebP starts with RIFF
        "extensions": [".webp"],
    },
    "image/gif": {
        "magic_bytes": [b"GIF87a", b"GIF89a"],
        "extensions": [".gif"],
    },
}

ALLOWED_MIME_TYPES = list(ALLOWED_TYPES.keys())


# === Helper Functions ===


def validate_file_content(file_content: bytes, declared_content_type: str) -> tuple[bool, str]:
    """
    Validate that file content matches declared content type using file magic.

    Returns:
        tuple: (is_valid, detected_mime_type)
    """
    try:
        # Use python-magic to detect actual file type
        detected_mime = magic.from_buffer(file_content[:2048], mime=True)

        # Check if detected type is allowed
        if detected_mime not in ALLOWED_MIME_TYPES:
            return False, detected_mime

        # Check if declared type matches (with some flexibility)
        # Allow image/jpeg when detected as image/jpeg, etc.
        if detected_mime == declared_content_type:
            return True, detected_mime

        # Special cases: some browsers send different MIME types
        if detected_mime == "image/jpeg" and declared_content_type in ["image/jpg", "image/pjpeg"]:
            return True, detected_mime

        # If detected is allowed but different from declared, use detected
        # This prevents type confusion attacks
        return True, detected_mime

    except Exception as e:
        logger.warning(
            "file_magic_detection_failed",
            error=str(e),
            declared_type=declared_content_type,
        )
        # Fall back to declared type if magic detection fails
        return declared_content_type in ALLOWED_MIME_TYPES, declared_content_type


def document_to_response(document) -> DocumentResponse:
    """Convert document model to response."""
    uploaded_at_iso = document.uploaded_at.isoformat()
    extracted_data = document.extracted_data or {}
    unclear_items = extracted_data.get("unclear_items", [])

    return DocumentResponse(
        id=document.id,
        transaction_id=document.transaction_id,
        document_type=document.document_type,
        filename=document.filename,
        content_type=document.content_type,
        file_size=document.file_size,
        status=document.status,
        extraction_status=document.status,  # Frontend uses extraction_status
        extraction_confidence=document.extraction_confidence,
        confidence_score=document.extraction_confidence,  # Alias for frontend
        needs_review=document.status == "needs_review",
        needs_review_reason=document.needs_review_reason,
        uploaded_at=uploaded_at_iso,
        created_at=uploaded_at_iso,  # Alias for frontend compatibility
        verified_at=document.verified_at.isoformat() if document.verified_at else None,
        flags=unclear_items,  # Derived from extracted_data
    )


# === Endpoints ===


@router.post(
    "/upload/{transaction_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentResponse,
)
async def upload_document(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    storage: StorageDep,
    file: UploadFile = File(...),
    document_type: str | None = Form(None),
) -> DocumentResponse:
    """
    Upload a document to a transaction.

    The document will be stored and queued for AI extraction.
    Document type will be auto-detected if not specified.

    Triggers:
    - DocumentExtractAgent for data extraction
    - ChecklistAgent for checklist updates
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Read file content for validation
    file_content = await file.read()

    if len(file_content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    # Validate content type using file magic (NEW-013 fix)
    declared_content_type = file.content_type or "application/pdf"
    is_valid, detected_content_type = validate_file_content(file_content, declared_content_type)

    if not is_valid:
        logger.warning(
            "document_upload_invalid_type",
            declared_type=declared_content_type,
            detected_type=detected_content_type,
            filename=file.filename,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Detected: {detected_content_type}. Allowed types: PDF, JPEG, PNG, TIFF, WebP, GIF",
        )

    # Use detected content type for storage
    content_type = detected_content_type

    # Upload to storage
    storage_path = None
    try:
        storage_path, file_size = await storage.upload_file(
            organization_id=current_user.organization_id,
            transaction_id=transaction_id,
            filename=file.filename,
            file_data=file_content,
            content_type=content_type,
        )
    except StorageError as e:
        logger.error(
            "document_upload_storage_failed",
            transaction_id=str(transaction_id),
            filename=file.filename,
            user_id=str(current_user.id),
            error=str(e),
        )
        # Don't expose internal storage details (NEW-008 fix)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        logger.error(
            "document_upload_unexpected_error",
            transaction_id=str(transaction_id),
            filename=file.filename,
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during upload.",
        )

    # Create document record and queue extraction
    try:
        document = await service.upload_document(
            transaction_id=transaction_id,
            organization_id=current_user.organization_id,
            uploaded_by=current_user.id,
            filename=file.filename,
            storage_path=storage_path,
            content_type=content_type,
            file_size=file_size,
            document_type=document_type,
        )
        logger.info(
            "document_uploaded",
            document_id=str(document.id),
            transaction_id=str(transaction_id),
            user_id=str(current_user.id),
            filename=file.filename,
            content_type=content_type,
            file_size=file_size,
        )
    except ValueError as e:
        # Clean up uploaded file on business logic error
        try:
            await storage.delete_file(storage_path)
            logger.info(
                "document_upload_cleanup_success",
                storage_path=storage_path,
            )
        except Exception as cleanup_error:
            logger.error(
                "document_upload_cleanup_failed",
                storage_path=storage_path,
                error=str(cleanup_error),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return document_to_response(document)


@router.post(
    "/upload-url/{transaction_id}",
    response_model=UploadUrlResponse,
)
async def get_upload_url(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    storage: StorageDep,
    filename: str,
    content_type: str = "application/pdf",
) -> UploadUrlResponse:
    """
    Get a presigned URL for direct upload.

    Use this for larger files or when uploading from the client directly.
    After uploading, call POST /documents/confirm to create the document record.
    """
    # Validate content type
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    try:
        upload_url, storage_path = await storage.get_presigned_upload_url(
            organization_id=current_user.organization_id,
            transaction_id=transaction_id,
            filename=filename,
            content_type=content_type,
        )
    except StorageError as e:
        logger.error(
            "document_presigned_url_failed",
            transaction_id=str(transaction_id),
            filename=filename,
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service temporarily unavailable.",
        )

    return UploadUrlResponse(
        upload_url=upload_url,
        storage_path=storage_path,
        expires_in=3600,
    )


@router.get("/transaction/{transaction_id}", response_model=list[DocumentResponse])
async def list_transaction_documents(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    document_type: str | None = None,
    status_filter: str | None = None,
) -> list[DocumentResponse]:
    """Get all documents for a transaction."""
    documents = await service.get_transaction_documents(
        transaction_id,
        current_user.organization_id,
        document_type=document_type,
        status=status_filter,
    )

    return [document_to_response(d) for d in documents]


@router.get("/review-queue", response_model=list[DocumentResponse])
async def get_review_queue(
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> list[DocumentResponse]:
    """Get documents needing human review."""
    documents = await service.get_review_queue(current_user.organization_id)
    return [document_to_response(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Get document metadata and status."""
    document = await service.get_document(document_id, current_user.organization_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document_to_response(document)


@router.get("/{document_id}/download", response_model=PresignedUrlResponse)
async def download_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    storage: StorageDep,
) -> PresignedUrlResponse:
    """
    Get a presigned URL for document download.

    Returns a URL valid for 1 hour that allows direct download from storage.
    """
    document = await service.get_document(document_id, current_user.organization_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        url = await storage.get_presigned_download_url(document.storage_path)
    except StorageError as e:
        logger.error(
            "document_download_url_failed",
            document_id=str(document_id),
            storage_path=document.storage_path,
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service temporarily unavailable.",
        )

    return PresignedUrlResponse(url=url, expires_in=3600)


@router.get("/{document_id}/extracted", response_model=ExtractedDataResponse)
async def get_extracted_data(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> ExtractedDataResponse:
    """
    Get the AI-extracted data from a document.

    Returns structured data parsed from the document along
    with confidence scores and items requiring review.
    """
    document = await service.get_document(document_id, current_user.organization_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if document.status == "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is still being processed",
        )

    extracted_data = document.extracted_data or {}
    unclear_items = extracted_data.get("unclear_items", [])

    return ExtractedDataResponse(
        document_id=document.id,
        document_type=document.document_type,
        extracted_data=extracted_data,
        confidence=document.extraction_confidence,
        needs_review_items=unclear_items,
    )


@router.post("/{document_id}/verify", response_model=DocumentResponse)
async def verify_extracted_data(
    document_id: UUID,
    request: VerifyDocumentRequest,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """
    Verify or correct AI-extracted data.

    Human-in-the-loop confirmation of extracted data.
    Any corrections provided will update the stored data.

    Triggers:
    - DeadlineAgent if dates were confirmed/corrected
    - ChecklistAgent for document status update
    """
    document = await service.verify_document(
        document_id,
        current_user.organization_id,
        verified_by=current_user.id,
        corrections=request.corrections,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    logger.info(
        "document_verified",
        document_id=str(document_id),
        user_id=str(current_user.id),
        has_corrections=request.corrections is not None,
    )

    return document_to_response(document)


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """
    Re-run AI extraction on a document.

    Useful if extraction failed or new extraction capabilities
    are available.
    """
    document = await service.reprocess_document(
        document_id,
        current_user.organization_id,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    logger.info(
        "document_reprocess_requested",
        document_id=str(document_id),
        user_id=str(current_user.id),
    )

    return document_to_response(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    storage: StorageDep,
) -> None:
    """
    Delete a document from a transaction.

    Deletes both the storage file and the database record.
    Storage deletion is logged but does not block database deletion.
    """
    # Get document to get storage path
    document = await service.get_document(document_id, current_user.organization_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    storage_path = document.storage_path
    transaction_id = document.transaction_id

    # Delete from storage first (NEW-003, NEW-019 fix - proper logging)
    storage_deleted = False
    try:
        await storage.delete_file(storage_path)
        storage_deleted = True
        logger.info(
            "document_storage_deleted",
            document_id=str(document_id),
            storage_path=storage_path,
            user_id=str(current_user.id),
        )
    except StorageError as e:
        # Log but continue - database record should still be deleted
        # so user doesn't have a "stuck" document
        logger.error(
            "document_storage_delete_failed",
            document_id=str(document_id),
            storage_path=storage_path,
            user_id=str(current_user.id),
            error=str(e),
            will_orphan_file=True,
        )
    except Exception as e:
        logger.error(
            "document_storage_delete_unexpected_error",
            document_id=str(document_id),
            storage_path=storage_path,
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
            will_orphan_file=True,
        )

    # Delete database record
    deleted = await service.delete_document(document_id, current_user.organization_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Audit log for document deletion (NEW-021 fix)
    logger.info(
        "document_deleted",
        document_id=str(document_id),
        transaction_id=str(transaction_id),
        user_id=str(current_user.id),
        storage_deleted=storage_deleted,
        storage_path=storage_path,
    )
