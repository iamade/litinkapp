import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.services.storage import S3StorageService


def _stream_client(chunks=None, status_error=None, raise_on_enter=None):
    """Build a mock httpx.AsyncClient matching the post-e265e8f product shape.

    The product calls `async with client.stream("GET", url) as response` and then
    iterates `response.aiter_bytes(chunk_size=...)`, so `stream` must be a plain
    callable returning an async context manager (not a coroutine).
    """
    chunks = chunks if chunks is not None else [b"fake-bytes"]

    class _Stream:
        async def __aenter__(self_inner):
            if raise_on_enter is not None:
                raise raise_on_enter
            response = MagicMock()
            response.status_code = 200
            if status_error is not None:
                response.raise_for_status = MagicMock(side_effect=status_error)
            else:
                response.raise_for_status = MagicMock()

            async def _aiter_bytes(chunk_size=None):
                for c in chunks:
                    yield c

            response.aiter_bytes = _aiter_bytes
            return response

        async def __aexit__(self_inner, *exc):
            return False

    client = MagicMock()
    client.stream = MagicMock(side_effect=lambda *a, **k: _Stream())
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestBuildMediaPath:
    def test_image_path(self):
        path = S3StorageService.build_media_path("user-123", "images", "record-456", "png")
        assert path == "users/user-123/images/record-456.png"

    def test_audio_path(self):
        path = S3StorageService.build_media_path("user-123", "audio", "record-789", "mp3")
        assert path == "users/user-123/audio/record-789.mp3"

    def test_video_path(self):
        path = S3StorageService.build_media_path("user-123", "video", "record-abc", "mp4")
        assert path == "users/user-123/video/record-abc.mp4"

    def test_system_user(self):
        path = S3StorageService.build_media_path("system", "images", "rec-1", "png")
        assert path == "users/system/images/rec-1.png"


class TestPersistFromUrl:
    @staticmethod
    def _storage():
        storage = MagicMock(spec=S3StorageService)
        storage.upload_stream = AsyncMock(return_value="https://s3.example.com/media/user/images/rec.png")
        storage.persist_from_url = S3StorageService.persist_from_url.__get__(storage, S3StorageService)
        return storage

    @pytest.mark.asyncio
    async def test_successful_persist(self):
        """persist_from_url streams the download and hands the buffer to upload_stream"""
        storage = self._storage()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = _stream_client(chunks=[b"fake-", b"image-bytes"])
            mock_client_cls.return_value = mock_client
            result = await storage.persist_from_url(
                "https://pub-cdn.modelslab.com/image.png",
                "media/user/images/rec.png",
                content_type="image/png",
            )
        assert result == "https://s3.example.com/media/user/images/rec.png"
        mock_client.stream.assert_called_once_with("GET", "https://pub-cdn.modelslab.com/image.png")
        storage.upload_stream.assert_awaited_once()
        buffer = storage.upload_stream.await_args.args[0]
        assert buffer.read() == b"fake-image-bytes"
        assert storage.upload_stream.await_args.args[1] == "media/user/images/rec.png"
        assert storage.upload_stream.await_args.kwargs["content_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_404_retries(self):
        """persist_from_url retries a transient 404 and succeeds on the next attempt"""
        import httpx

        storage = self._storage()
        error_response = MagicMock()
        error_response.status_code = 404
        failing = _stream_client(
            status_error=httpx.HTTPStatusError("404", request=MagicMock(), response=error_response)
        )
        succeeding = _stream_client(chunks=[b"image-data"])
        with patch("httpx.AsyncClient", side_effect=[failing, succeeding]) as mock_client_cls, \
                patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            result = await storage.persist_from_url(
                "https://pub-cdn.modelslab.com/image.png",
                "media/user/images/rec.png",
                max_retries=3,
            )
        assert result == "https://s3.example.com/media/user/images/rec.png"
        assert mock_client_cls.call_count == 2
        assert failing.stream.call_count == 1 and succeeding.stream.call_count == 1
        mock_sleep.assert_awaited_once_with(1)
        storage.upload_stream.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_all_retries_fail(self):
        """After max_retries the ORIGINAL httpx error is re-raised (the product wraps nothing)"""
        import httpx

        storage = self._storage()
        error_response = MagicMock()
        error_response.status_code = 500
        clients = [
            _stream_client(
                status_error=httpx.HTTPStatusError("500", request=MagicMock(), response=error_response)
            )
            for _ in range(2)
        ]
        with patch("httpx.AsyncClient", side_effect=clients) as mock_client_cls, \
                patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(httpx.HTTPStatusError, match="500"):
                await storage.persist_from_url(
                    "https://cdn.example.com/fail.png",
                    "media/user/images/rec.png",
                    max_retries=2,
                )
        assert mock_client_cls.call_count == 2
        storage.upload_stream.assert_not_awaited()
