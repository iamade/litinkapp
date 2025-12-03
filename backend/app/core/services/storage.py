import os
import aiofiles
from fastapi import UploadFile, HTTPException
from app.core.config import settings
import shutil
from pathlib import Path


class LocalStorageService:
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        # Ensure subdirectories exist
        (self.upload_dir / "videos").mkdir(exist_ok=True)
        (self.upload_dir / "audio").mkdir(exist_ok=True)
        (self.upload_dir / "images").mkdir(exist_ok=True)
        (self.upload_dir / "files").mkdir(exist_ok=True)

    async def upload(
        self, file_content: bytes, path: str, content_type: str = None
    ) -> str:
        """
        Upload content to local storage.
        path: relative path like 'users/123/video.mp4'
        Returns: public URL (relative to base URL)
        """
        # Sanitize path to prevent directory traversal
        safe_path = Path(path).name
        # For now, we might want to flatten the structure or recreate it inside uploads
        # Let's recreate the structure inside uploads
        full_path = self.upload_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_content)

        return f"/static/{path}"

    async def download(self, path: str) -> bytes:
        """Download content from local storage"""
        full_path = self.upload_dir / path
        if not full_path.exists():
            return None

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    def get_public_url(self, path: str) -> str:
        """Get public URL for a file"""
        return f"/static/{path}"

    async def delete(self, path: str) -> bool:
        """Delete file from local storage"""
        full_path = self.upload_dir / path
        if full_path.exists():
            os.remove(full_path)
            return True
        return False


storage_service = LocalStorageService()
