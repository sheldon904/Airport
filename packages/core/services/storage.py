"""Storage service - S3-compatible object storage with async support.

All S3 operations are run in a thread pool to prevent blocking the async event loop.
"""

import asyncio
import io
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from typing import BinaryIO
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import structlog

from packages.core.config import settings
from packages.core.exceptions import StorageError

logger = structlog.get_logger()

# Thread pool for S3 operations - shared across all storage service instances
_s3_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="s3_worker")


class StorageService:
    """
    Service for S3-compatible object storage.

    Handles:
    - Document upload/download
    - Presigned URL generation
    - File organization by tenant

    All S3 operations run in a thread pool to avoid blocking the async event loop.
    """

    def __init__(self) -> None:
        # Configure S3 client
        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )

        client_kwargs = {
            "service_name": "s3",
            "config": config,
            "region_name": settings.aws_region,
        }

        # Use custom endpoint for MinIO in development
        if settings.storage_endpoint:
            client_kwargs["endpoint_url"] = settings.storage_endpoint

        if settings.aws_access_key_id:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

        self.client = boto3.client(**client_kwargs)
        self.bucket = settings.storage_bucket

    def _get_key(
        self,
        organization_id: UUID,
        transaction_id: UUID,
        filename: str,
    ) -> str:
        """Generate storage key with tenant isolation."""
        # Format: org_id/transaction_id/timestamp_filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Sanitize filename to prevent path traversal
        safe_filename = self._sanitize_filename(filename)
        return f"{organization_id}/{transaction_id}/{timestamp}_{safe_filename}"

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other security issues.

        - Removes path separators
        - Replaces spaces with underscores
        - Removes control characters
        - Limits length to 255 characters
        """
        if not filename:
            return "unnamed_file"

        # Remove any path components (prevent traversal)
        filename = filename.replace("/", "_").replace("\\", "_")
        filename = filename.replace("..", "_")

        # Replace spaces
        filename = filename.replace(" ", "_")

        # Remove control characters and null bytes
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)

        # Limit length
        if len(filename) > 255:
            # Keep extension if present
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                max_name_len = 255 - len(ext) - 1
                filename = f"{name[:max_name_len]}.{ext}"
            else:
                filename = filename[:255]

        return filename or "unnamed_file"

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a synchronous function in the thread pool executor."""
        loop = asyncio.get_event_loop()
        if kwargs:
            func = partial(func, **kwargs)
        return await loop.run_in_executor(_s3_executor, func, *args)

    async def upload_file(
        self,
        *,
        organization_id: UUID,
        transaction_id: UUID,
        filename: str,
        file_data: BinaryIO | bytes,
        content_type: str = "application/pdf",
    ) -> tuple[str, int]:
        """
        Upload a file to storage.

        Returns:
            tuple: (storage_path, file_size)

        Raises:
            StorageError: If upload fails
        """
        key = self._get_key(organization_id, transaction_id, filename)

        # Handle both file objects and bytes
        if isinstance(file_data, bytes):
            file_obj = io.BytesIO(file_data)
            file_size = len(file_data)
        else:
            file_obj = file_data
            # Get file size
            file_obj.seek(0, 2)
            file_size = file_obj.tell()
            file_obj.seek(0)

        def _do_upload():
            self.client.upload_fileobj(
                file_obj,
                self.bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {
                        "organization_id": str(organization_id),
                        "transaction_id": str(transaction_id),
                        "original_filename": self._sanitize_filename(filename),
                    },
                },
            )

        try:
            await self._run_in_executor(_do_upload)
            logger.info(
                "storage_file_uploaded",
                key=key,
                size=file_size,
                content_type=content_type,
            )
        except ClientError as e:
            logger.error(
                "storage_upload_failed",
                key=key,
                error=str(e),
                error_code=e.response.get("Error", {}).get("Code"),
            )
            raise StorageError(f"Failed to upload file: {e.response['Error']['Code']}")

        return key, file_size

    async def download_file(self, storage_path: str) -> bytes:
        """
        Download a file from storage.

        Raises:
            StorageError: If file not found or download fails
        """
        def _do_download():
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=storage_path,
            )
            return response["Body"].read()

        try:
            data = await self._run_in_executor(_do_download)
            logger.debug("storage_file_downloaded", key=storage_path, size=len(data))
            return data
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                logger.warning("storage_file_not_found", key=storage_path)
                raise StorageError(f"File not found: {storage_path}")
            logger.error(
                "storage_download_failed",
                key=storage_path,
                error=str(e),
                error_code=error_code,
            )
            raise StorageError(f"Failed to download file: {error_code}")

    async def get_presigned_download_url(
        self,
        storage_path: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned URL for direct download.

        Args:
            storage_path: The S3 key of the file
            expires_in: URL validity in seconds (default 1 hour)

        Raises:
            StorageError: If URL generation fails
        """
        def _do_generate():
            return self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": storage_path,
                },
                ExpiresIn=expires_in,
            )

        try:
            url = await self._run_in_executor(_do_generate)
            return url
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "storage_presigned_url_failed",
                key=storage_path,
                error=str(e),
                error_code=error_code,
            )
            raise StorageError(f"Failed to generate download URL: {error_code}")

    async def get_presigned_upload_url(
        self,
        organization_id: UUID,
        transaction_id: UUID,
        filename: str,
        content_type: str = "application/pdf",
        expires_in: int = 3600,
    ) -> tuple[str, str]:
        """
        Generate a presigned URL for direct upload.

        Returns:
            tuple: (upload_url, storage_path)

        Raises:
            StorageError: If URL generation fails
        """
        key = self._get_key(organization_id, transaction_id, filename)

        def _do_generate():
            return self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

        try:
            url = await self._run_in_executor(_do_generate)
            return url, key
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "storage_presigned_upload_url_failed",
                key=key,
                error=str(e),
                error_code=error_code,
            )
            raise StorageError(f"Failed to generate upload URL: {error_code}")

    async def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from storage.

        Returns:
            bool: True if deletion succeeded

        Raises:
            StorageError: If deletion fails
        """
        def _do_delete():
            self.client.delete_object(
                Bucket=self.bucket,
                Key=storage_path,
            )

        try:
            await self._run_in_executor(_do_delete)
            logger.info("storage_file_deleted", key=storage_path)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "storage_delete_failed",
                key=storage_path,
                error=str(e),
                error_code=error_code,
            )
            raise StorageError(f"Failed to delete file: {error_code}")

    async def file_exists(self, storage_path: str) -> bool:
        """Check if a file exists in storage."""
        def _do_head():
            self.client.head_object(
                Bucket=self.bucket,
                Key=storage_path,
            )

        try:
            await self._run_in_executor(_do_head)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                return False
            logger.error(
                "storage_head_failed",
                key=storage_path,
                error=str(e),
                error_code=error_code,
            )
            raise StorageError(f"Failed to check file existence: {error_code}")

    async def ensure_bucket_exists(self) -> None:
        """Ensure the storage bucket exists (for initialization)."""
        def _do_head_bucket():
            self.client.head_bucket(Bucket=self.bucket)

        def _do_create_bucket():
            create_args = {"Bucket": self.bucket}
            if settings.aws_region != "us-east-1":
                create_args["CreateBucketConfiguration"] = {
                    "LocationConstraint": settings.aws_region,
                }
            self.client.create_bucket(**create_args)

        try:
            await self._run_in_executor(_do_head_bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                # Create bucket
                try:
                    await self._run_in_executor(_do_create_bucket)
                    logger.info("storage_bucket_created", bucket=self.bucket)
                except ClientError as create_error:
                    create_error_code = create_error.response.get("Error", {}).get("Code", "Unknown")
                    logger.error(
                        "storage_bucket_create_failed",
                        bucket=self.bucket,
                        error=str(create_error),
                        error_code=create_error_code,
                    )
                    raise StorageError(f"Failed to create bucket: {create_error_code}")
            else:
                logger.error(
                    "storage_bucket_check_failed",
                    bucket=self.bucket,
                    error=str(e),
                    error_code=error_code,
                )
                raise StorageError(f"Failed to check bucket: {error_code}")


# Singleton instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
