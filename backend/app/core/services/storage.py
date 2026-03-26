from __future__ import annotations
import os
import io
import mimetypes
from typing import Optional, BinaryIO, Tuple
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

    async def persist_from_url(
        self,
        source_url: str,
        dest_path: str,
        content_type: Optional[str] = None,
        max_retries: int = 3,
        timeout_seconds: int = 120,
    ) -> str:
        """
        Download a file from an external URL and upload it to our S3 storage.

        This is used to persist ephemeral CDN URLs (e.g. ModelsLab) into our
        own permanent storage before the CDN purges them.

        Args:
            source_url: External URL to download from (e.g. ModelsLab CDN)
            dest_path: S3 object key (e.g. media/{user_id}/images/{record_id}.png)
            content_type: Optional MIME type override; auto-detected if not provided
            max_retries: Number of download retries with exponential backoff
            timeout_seconds: HTTP request timeout for the download

        Returns:
            Public URL of the persisted file in our S3 storage

        Raises:
            Exception: If download or upload fails after all retries
        """
        import httpx
        import asyncio

        last_error = None

        for attempt in range(max_retries):
            try:
                # Download from source URL with streaming
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout_seconds),
                    follow_redirects=True,
                ) as client:
                    response = await client.get(source_url)
                    response.raise_for_status()

                    file_bytes = response.content

                    # Auto-detect content type from response headers or URL
                    if not content_type:
                        content_type = response.headers.get("content-type", "").split(";")[0].strip()
                        if not content_type or content_type == "application/octet-stream":
                            # Guess from URL extension
                            guessed, _ = mimetypes.guess_type(source_url.split("?")[0])
                            content_type = guessed or "application/octet-stream"

                # Upload to our S3 storage
                permanent_url = await self.upload(file_bytes, dest_path, content_type)

                logger.info(
                    f"[Storage] Persisted {len(file_bytes)} bytes from external URL to {dest_path}"
                )
                return permanent_url

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 404:
                    # CDN hasn't propagated yet, retry with backoff
                    logger.warning(
                        f"[Storage] Source URL returned 404 (attempt {attempt + 1}/{max_retries}): {source_url}"
                    )
                else:
                    logger.warning(
                        f"[Storage] Download failed with HTTP {e.response.status_code} (attempt {attempt + 1}/{max_retries}): {source_url}"
                    )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt * 3)  # 3s, 6s, 12s

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[Storage] persist_from_url failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt * 3)

        raise Exception(
            f"Failed to persist file from {source_url} after {max_retries} attempts: {last_error}"
        )

    @staticmethod
    def build_media_path(
        user_id: str,
        media_type: str,
        record_id: str,
        extension: str = "png",
    ) -> str:
        """
        Build a structured S3 path for persisted media.

        Args:
            user_id: User UUID
            media_type: 'images', 'audio', or 'video'
            record_id: Database record UUID
            extension: File extension (png, mp3, mp4, etc.)

        Returns:
            S3 object key like media/{user_id}/images/{record_id}.png
        """
        return f"media/{user_id}/{media_type}/{record_id}.{extension}"

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
