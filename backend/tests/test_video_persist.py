import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.services.storage import S3StorageService

class TestVideoPersistToS3:
    def test_video_media_path(self):
        path = S3StorageService.build_media_path('user-1', 'video', 'rec-1', 'mp4')
        assert path == 'media/user-1/video/rec-1.mp4'

    @pytest.mark.asyncio
    async def test_persist_video_from_url(self):
        """Video persist should use same persist_from_url with video content type"""
        storage = MagicMock(spec=S3StorageService)
        storage.upload = AsyncMock(return_value='https://s3.example.com/media/user/video/rec.mp4')
        storage.persist_from_url = S3StorageService.persist_from_url.__get__(storage, S3StorageService)
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.content = b'fake-video-bytes'
            mock_response.headers = {'content-type': 'video/mp4'}
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client
            result = await storage.persist_from_url('https://pub-cdn.modelslab.com/video.mp4', 'media/user/video/rec.mp4', content_type='video/mp4')
            assert result == 'https://s3.example.com/media/user/video/rec.mp4'
