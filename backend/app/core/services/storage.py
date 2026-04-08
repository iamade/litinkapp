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

        import os as _os

        print(
            f"[STORAGE INIT] USE_MINIO={self.use_minio} (type={type(self.use_minio).__name__})"
        )
        print(
            f"[STORAGE INIT] Raw env S3_BUCKET_NAME={_os.environ.get('S3_BUCKET_NAME', 'NOT SET')}"
        )
        print(f"[STORAGE INIT] Settings S3_BUCKET_NAME={settings.S3_BUCKET_NAME}")
        print(f"[STORAGE INIT] Settings MINIO_BUCKET_NAME={settings.MINIO_BUCKET_NAME}")

        if self.use_minio:
            # MinIO configuration for local development
            print(
                f"[STORAGE INIT] Using MinIO - endpoint={settings.MINIO_ENDPOINT}, bucket={settings.MINIO_BUCKET_NAME}"
            )
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
            print(
                f"[STORAGE INIT] Using S3 - endpoint={settings.S3_ENDPOINT}, bucket={settings.S3_BUCKET_NAME}, region={settings.S3_REGION}"
            )
            print(
                f"[STORAGE INIT] S3 access key starts with: {settings.S3_ACCESS_KEY[:8] if settings.S3_ACCESS_KEY else 'NOT SET'}..."
            )
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT if settings.S3_ENDPOINT else None,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                ),
            )
            self.bucket_name = settings.S3_BUCKET_NAME

        print(f"[STORAGE INIT] Final bucket_name={self.bucket_name}")

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
            logger.error(
                f"[STORAGE DEBUG] Bucket={self.bucket_name}, use_minio={self.use_minio}"
            )
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

    @staticmethod
    def build_media_path(
        user_id: str,
        media_type: str,
        record_id: str,
        extension: str,
        scope_id: Optional[str] = None,
    ) -> str:
        """Build a standardized S3 path for media files."""
        ext = extension.lstrip(".")
        if scope_id:
            return f"users/{user_id}/{media_type}/scope-{scope_id}/{record_id}.{ext}"
        return f"users/{user_id}/{media_type}/{record_id}.{ext}"

    async def persist_from_url(self, source_url: str, dest_path: str, content_type: Optional[str] = None, timeout_seconds: int = 120, max_retries: int = 3) -> str:
        """Download from external URL and persist to our S3 storage.

        Streams the response into an in-memory buffer to avoid holding the
        entire payload in the httpx response object, then uploads via
        upload_stream for better memory efficiency on large files.
        """
        import httpx
        import asyncio
        import io

        last_error = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=float(timeout_seconds), follow_redirects=True) as client:
                    async with client.stream("GET", source_url) as response:
                        response.raise_for_status()
                        buffer = io.BytesIO()
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            buffer.write(chunk)
                        buffer.seek(0)
                        return await self.upload_stream(buffer, dest_path, content_type=content_type)
            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code
                is_transient = status == 429 or status >= 500 or status == 404
                if is_transient and attempt < max_retries - 1:
                    logger.warning(f"[persist_from_url] HTTP {status} for {source_url}, retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"[persist_from_url] Error for {source_url}, retry {attempt + 1}/{max_retries}: {e}")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        raise last_error  # type: ignore[misc]

    def _strip_url_prefix(self, path: str) -> str:
        """Strip full URL prefix from storage path, returning just the object key.

        Handles cases where storage_path was stored as a full public URL
        (e.g. http://localhost:9000/bucket/users/123/file.pdf) instead of
        just the key (users/123/file.pdf).
        """
        if not path or not path.startswith(("http://", "https://")):
            return path

        # Build expected prefix based on storage backend
        if self.use_minio:
            prefix = f"{settings.MINIO_PUBLIC_URL}/{self.bucket_name}/"
        elif settings.S3_ENDPOINT:
            prefix = f"{settings.S3_ENDPOINT}/{self.bucket_name}/"
        else:
            prefix = f"https://{self.bucket_name}.s3.{settings.S3_REGION}.amazonaws.com/"

        if path.startswith(prefix):
            return path[len(prefix):]

        # Fallback: find /{bucket_name}/ anywhere in the URL
        bucket_marker = f"/{self.bucket_name}/"
        idx = path.find(bucket_marker)
        if idx != -1:
            return path[idx + len(bucket_marker):]

        return path

    async def download(self, path: str) -> Optional[bytes]:
        """Download file from storage"""
        try:
            path = self._strip_url_prefix(path)
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
            # Supabase public buckets require object/public URLs, not the S3 API path.
            base = (
                settings.S3_ENDPOINT.replace("/storage/v1/s3", "/storage/v1/object/public")
                if "/storage/v1/s3" in settings.S3_ENDPOINT
                else settings.S3_ENDPOINT
            )
            return f"{base}/{self.bucket_name}/{path}"
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
