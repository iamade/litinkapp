import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.services import ffmpeg_utils


@pytest.mark.asyncio
async def test_extract_last_frame_uses_internal_minio_endpoint_for_download(monkeypatch):
    monkeypatch.setattr(ffmpeg_utils.settings, "MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr(ffmpeg_utils.settings, "MINIO_ENDPOINT", "http://minio:9000")

    requested_urls = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            requested_urls.append(url)
            return SimpleNamespace(status_code=200, content=b"fake-video")

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    def fake_run(cmd, capture_output=True, text=False, check=False):
        if cmd[0] == "ffprobe":
            return SimpleNamespace(stdout="1.0\n", returncode=0)
        if cmd[0] == "ffmpeg":
            frame_path = cmd[-1]
            with open(frame_path, "wb") as frame_file:
                frame_file.write(b"fake-frame")
            return SimpleNamespace(stdout="", returncode=0)
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", fake_run)

    storage = MagicMock()
    storage.upload = AsyncMock(return_value="http://localhost:9000/litink-books/frames/user/last.jpg")
    monkeypatch.setattr("app.core.services.storage.get_storage_service", lambda: storage)

    result = await ffmpeg_utils.extract_last_frame(
        "http://localhost:9000/litink-books/videos/generated.mp4",
        user_id="user-123",
    )

    assert requested_urls == ["http://minio:9000/litink-books/videos/generated.mp4"]
    assert result == "http://localhost:9000/litink-books/frames/user/last.jpg"
    storage.upload.assert_awaited_once()
    upload_args, upload_kwargs = storage.upload.await_args
    assert upload_args[0] == b"fake-frame"
    assert upload_args[1].startswith("frames/user-123/last_frame_")
    assert upload_args[1].endswith(".jpg")
    assert upload_kwargs == {"content_type": "image/jpeg"}
