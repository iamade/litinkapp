from __future__ import annotations
import os
from typing import Optional, BinaryIO
from pathlib import Path
from app.core.config import settings
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class S3StorageService:
    """
    S3-compatible storage service that works with:
    - MinIO for local development
    - Supabase Storage for production (S3-compatible)
    - AWS S3 for production

    This is memory-efficient as it streams files rather than loading them entirely into memory.
    """

    def __init__(self):
        self.use_minio = settings.USE_MINIO  # Set in config based on environment

        if self.use_minio:
            # MinIO configuration for local development
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.MINIO_ENDPOINT,  # e.g., 'http://localhost:9000'
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",
            )
            self.bucket_name = settings.MINIO_BUCKET_NAME
        else:
            # S3-compatible storage for production (AWS S3 or Supabase Storage S3)
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT if settings.S3_ENDPOINT else None,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
            )
            self.bucket_name = settings.S3_BUCKET_NAME

        # Ensure bucket exists (for MinIO)
        if self.use_minio:
            self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist (MinIO only)"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to create bucket: {e}")

    async def upload(
        self, file_content: bytes, path: str, content_type: Optional[str] = None
    ) -> str:
        """
        Upload file to S3-compatible storage.
        Returns: public URL
        """
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            # Upload using put_object (memory-efficient for bytes)
            self.client.put_object(
                Bucket=self.bucket_name, Key=path, Body=file_content, **extra_args
            )

            # Generate public URL
            if self.use_minio:
                return f"{settings.MINIO_PUBLIC_URL}/{self.bucket_name}/{path}"
            else:
                # For S3/Supabase, generate presigned URL or use CDN
                return self.get_public_url(path)

        except Exception as e:
            logger.error(f"Upload failed for {path}: {e}")
            raise

    async def upload_stream(
        self, file_stream: BinaryIO, path: str, content_type: Optional[str] = None
    ) -> str:
        """
        Upload file from stream (most memory-efficient).
        Use this for large files to avoid loading into memory.
        """
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            self.client.upload_fileobj(
                file_stream, self.bucket_name, path, ExtraArgs=extra_args
            )

            if self.use_minio:
                return f"{settings.MINIO_PUBLIC_URL}/{self.bucket_name}/{path}"
            else:
                return self.get_public_url(path)

        except Exception as e:
            logger.error(f"Stream upload failed for {path}: {e}")
            raise

    async def download(self, path: str) -> Optional[bytes]:
        """Download file from storage"""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=path)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def get_public_url(self, path: str) -> str:
        """Get public URL for a file"""
        if self.use_minio:
            return f"{settings.MINIO_PUBLIC_URL}/{self.bucket_name}/{path}"
        elif settings.S3_ENDPOINT:
            # Supabase Storage or other S3-compatible with custom endpoint
            return f"{settings.S3_ENDPOINT}/{self.bucket_name}/{path}"
        else:
            # AWS S3 public URL
            return f"https://{self.bucket_name}.s3.{settings.S3_REGION}.amazonaws.com/{path}"

    async def delete(self, path: str) -> bool:
        """Delete file from storage"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=path)
            return True
        except Exception as e:
            logger.error(f"Delete failed for {path}: {e}")
            return False

    def list(self, prefix: str) -> list:
        """
        List files with given prefix.
        Returns list of dicts with 'name' key (filename only, not full path).
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )

            if "Contents" not in response:
                return []

            files = []
            for obj in response["Contents"]:
                # Extract just the filename from the full key
                filename = obj["Key"].split("/")[-1]
                files.append({"name": filename})

            return files
        except Exception as e:
            logger.error(f"List failed for prefix {prefix}: {e}")
            return []

    async def remove_batch(self, paths: list[str]) -> dict:
        """Remove multiple files at once"""
        try:
            objects = [{"Key": path} for path in paths]
            response = self.client.delete_objects(
                Bucket=self.bucket_name, Delete={"Objects": objects}
            )

            deleted_count = len(response.get("Deleted", []))
            return {"deleted": deleted_count, "total": len(paths)}
        except Exception as e:
            logger.error(f"Batch delete failed: {e}")
            return {"deleted": 0, "total": len(paths)}

    async def delete_directory(self, prefix: str) -> bool:
        """Delete all files with given prefix (simulates directory deletion)"""
        try:
            # List all objects with the prefix
            objects = self.list(prefix)
            if not objects:
                return True

            # Delete all objects
            paths = [f"{prefix}/{obj['name']}" for obj in objects]
            await self.remove_batch(paths)
            return True
        except Exception as e:
            logger.error(f"Directory delete failed for {prefix}: {e}")
            return False


# Lazy singleton — only instantiated on first access
_storage_service: Optional[S3StorageService] = None


def get_storage_service() -> S3StorageService:
    """Get the storage service singleton, initializing it on first call."""
    global _storage_service
    if _storage_service is None:
        _storage_service = S3StorageService()
    return _storage_service


# For backward compatibility — lazy property
class _LazyStorageService:
    """Proxy that delays S3StorageService initialization until first use."""

    _instance: Optional[S3StorageService] = None

    def __getattr__(self, name):
        if _LazyStorageService._instance is None:
            _LazyStorageService._instance = S3StorageService()
        return getattr(_LazyStorageService._instance, name)


storage_service = _LazyStorageService()
