import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.services.storage import S3StorageService


class TestBuildMediaPath:
    def test_image_path(self):
        path = S3StorageService.build_media_path("user-123", "images", "record-456", "png")
        assert path == "media/user-123/images/record-456.png"

    def test_audio_path(self):
        path = S3StorageService.build_media_path("user-123", "audio", "record-789", "mp3")
        assert path == "media/user-123/audio/record-789.mp3"

    def test_video_path(self):
        path = S3StorageService.build_media_path("user-123", "video", "record-abc", "mp4")
        assert path == "media/user-123/video/record-abc.mp4"

    def test_system_user(self):
        path = S3StorageService.build_media_path("system", "images", "rec-1", "png")
        assert path == "media/system/images/rec-1.png"


class TestPersistFromUrl:
    @pytest.mark.asyncio
    async def test_successful_persist(self):
        """Test that persist_from_url downloads and uploads correctly"""
        storage = MagicMock(spec=S3StorageService)
        storage.upload = AsyncMock(return_value="https://s3.example.com/media/user/images/rec.png")
        storage.persist_from_url = S3StorageService.persist_from_url.__get__(storage, S3StorageService)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.content = b"fake-image-bytes"
            mock_response.headers = {"content-type": "image/png"}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await storage.persist_from_url(
                "https://pub-cdn.modelslab.com/image.png",
                "media/user/images/rec.png",
                content_type="image/png",
            )
            assert result == "https://s3.example.com/media/user/images/rec.png"
            storage.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_404_retries(self):
        """Test that persist_from_url retries on 404"""
        storage = MagicMock(spec=S3StorageService)
        storage.upload = AsyncMock(return_value="https://s3.example.com/test.png")
        storage.persist_from_url = S3StorageService.persist_from_url.__get__(storage, S3StorageService)

        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            error_response = MagicMock()
            error_response.status_code = 404

            success_response = AsyncMock()
            success_response.status_code = 200
            success_response.content = b"image-data"
            success_response.headers = {"content-type": "image/png"}
            success_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=[
                    httpx.HTTPStatusError("404", request=MagicMock(), response=error_response),
                    success_response,
                ]
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await storage.persist_from_url(
                "https://pub-cdn.modelslab.com/image.png",
                "media/user/images/rec.png",
                max_retries=3,
            )
            assert result == "https://s3.example.com/test.png"
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_all_retries_fail(self):
        """Test that persist_from_url raises after max retries"""
        storage = MagicMock(spec=S3StorageService)
        storage.persist_from_url = S3StorageService.persist_from_url.__get__(storage, S3StorageService)

        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            error_response = MagicMock()
            error_response.status_code = 500

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=error_response)
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(Exception, match="Failed to persist file"):
                await storage.persist_from_url(
                    "https://cdn.example.com/fail.png",
                    "media/user/images/rec.png",
                    max_retries=2,
                )
