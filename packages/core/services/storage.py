"""Storage service - S3-compatible object storage."""

import io
from datetime import datetime, timezone
from typing import BinaryIO
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from packages.core.config import settings
from packages.core.exceptions import StorageError


class StorageService:
    """
    Service for S3-compatible object storage.

    Handles:
    - Document upload/download
    - Presigned URL generation
    - File organization by tenant
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
        safe_filename = filename.replace(" ", "_")
        return f"{organization_id}/{transaction_id}/{timestamp}_{safe_filename}"

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

        try:
            self.client.upload_fileobj(
                file_obj,
                self.bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {
                        "organization_id": str(organization_id),
                        "transaction_id": str(transaction_id),
                        "original_filename": filename,
                    },
                },
            )
        except ClientError as e:
            raise StorageError(f"Failed to upload file: {e}")

        return key, file_size

    async def download_file(self, storage_path: str) -> bytes:
        """Download a file from storage."""
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=storage_path,
            )
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise StorageError(f"File not found: {storage_path}")
            raise StorageError(f"Failed to download file: {e}")

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
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": storage_path,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise StorageError(f"Failed to generate download URL: {e}")

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
        """
        key = self._get_key(organization_id, transaction_id, filename)

        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return url, key
        except ClientError as e:
            raise StorageError(f"Failed to generate upload URL: {e}")

    async def delete_file(self, storage_path: str) -> bool:
        """Delete a file from storage."""
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=storage_path,
            )
            return True
        except ClientError as e:
            raise StorageError(f"Failed to delete file: {e}")

    async def file_exists(self, storage_path: str) -> bool:
        """Check if a file exists in storage."""
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=storage_path,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise StorageError(f"Failed to check file existence: {e}")

    async def ensure_bucket_exists(self) -> None:
        """Ensure the storage bucket exists (for initialization)."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # Create bucket
                self.client.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={
                        "LocationConstraint": settings.aws_region,
                    }
                    if settings.aws_region != "us-east-1"
                    else {},
                )
            else:
                raise StorageError(f"Failed to check bucket: {e}")


# Singleton instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
