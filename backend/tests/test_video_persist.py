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

class TestVideoPersistToS3:
    def test_video_media_path(self):
        path = S3StorageService.build_media_path('user-1', 'video', 'rec-1', 'mp4')
        assert path == 'media/user-1/video/rec-1.mp4'

    @pytest.mark.asyncio
    async def test_persist_video_from_url(self):
        """Video persist should use the same persist_from_url stream path with a video content type"""
        storage = MagicMock(spec=S3StorageService)
        storage.upload_stream = AsyncMock(return_value='https://s3.example.com/media/user/video/rec.mp4')
        storage.persist_from_url = S3StorageService.persist_from_url.__get__(storage, S3StorageService)
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = _stream_client(chunks=[b'fake-video-', b'bytes'])
            mock_client_cls.return_value = mock_client
            result = await storage.persist_from_url('https://pub-cdn.modelslab.com/video.mp4', 'media/user/video/rec.mp4', content_type='video/mp4')
        assert result == 'https://s3.example.com/media/user/video/rec.mp4'
        mock_client.stream.assert_called_once_with('GET', 'https://pub-cdn.modelslab.com/video.mp4')
        storage.upload_stream.assert_awaited_once()
        assert storage.upload_stream.await_args.args[0].read() == b'fake-video-bytes'
        assert storage.upload_stream.await_args.kwargs['content_type'] == 'video/mp4'
