"""
File storage service for document management.

Supports S3 and local file storage.
"""
from typing import Optional
import os

from app.config import get_settings

settings = get_settings()


class StorageService:
    """Service for file storage operations."""

    def __init__(self):
        self.storage_type = settings.storage_type

        if self.storage_type == "s3":
            self._init_s3()
        else:
            self._init_local()

    def _init_s3(self):
        """Initialize S3 client."""
        import boto3

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        self.bucket = settings.s3_bucket

    def _init_local(self):
        """Initialize local storage."""
        self.local_path = os.path.join(os.getcwd(), "uploads")
        os.makedirs(self.local_path, exist_ok=True)

    async def generate_presigned_upload_url(
        self,
        file_key: str,
        content_type: str = "application/pdf",
        expires_in: int = 3600
    ) -> dict:
        """
        Generate presigned URL for direct upload to S3.

        Args:
            file_key: S3 key (path) for the file
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds

        Returns:
            Dict with upload_url and file_key
        """
        if self.storage_type != "s3":
            raise NotImplementedError("Presigned URLs only supported for S3")

        url = self.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": file_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )

        return {
            "upload_url": url,
            "file_key": file_key,
            "expires_in": expires_in,
        }

    async def generate_presigned_download_url(
        self,
        file_key: str,
        expires_in: int = 3600
    ) -> str:
        """
        Generate presigned URL for downloading from S3.

        Args:
            file_key: S3 key (path) for the file
            expires_in: URL expiration time in seconds

        Returns:
            Presigned download URL
        """
        if self.storage_type != "s3":
            raise NotImplementedError("Presigned URLs only supported for S3")

        url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": file_key,
            },
            ExpiresIn=expires_in,
        )

        return url

    async def save(self, content: bytes, file_key: str) -> str:
        """
        Save file content to storage.

        Args:
            content: File contents as bytes
            file_key: Path/key for the file

        Returns:
            Storage path/URL for the saved file
        """
        if self.storage_type == "s3":
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=content,
            )
            return f"s3://{self.bucket}/{file_key}"
        else:
            # Local storage
            full_path = os.path.join(self.local_path, file_key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(content)
            return full_path

    async def get(self, file_key: str) -> bytes:
        """
        Get file content from storage.

        Args:
            file_key: Path/key for the file

        Returns:
            File contents as bytes
        """
        if self.storage_type == "s3":
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=file_key,
            )
            return response["Body"].read()
        else:
            # Local storage
            full_path = os.path.join(self.local_path, file_key)
            with open(full_path, "rb") as f:
                return f.read()

    async def delete(self, file_key: str) -> bool:
        """
        Delete file from storage.

        Args:
            file_key: Path/key for the file

        Returns:
            True if deleted successfully
        """
        if self.storage_type == "s3":
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=file_key,
            )
            return True
        else:
            # Local storage
            full_path = os.path.join(self.local_path, file_key)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False


# Singleton instance
storage_service = StorageService() if settings.aws_access_key_id or settings.storage_type == "local" else None
