"""Unit tests for KAN-447: Kimi + GLM media adapters.

Tests cover:
  - Adapter initialization
  - Supported/unsupported modality handling
  - ProviderUnsupportedResult for modalities with no documented API
  - GLM image generation (sync + async) with mocked HTTP
  - GLM video generation (async) with mocked HTTP
  - Kimi all-modalities-unsupported
  - Media router SUPPORTED_PROVIDERS includes kimi and glm
  - Model config ladders include glm entries (additive, not reordered)
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.core.services.glm_media_adapter import (
    GLMMediaAdapter,
    ProviderUnsupportedResult,
)
from app.core.services.kimi_adapter import KimiMediaAdapter
from app.core.services.media_router import MediaRouter


# ---------------------------------------------------------------------------
# Kimi adapter tests
# ---------------------------------------------------------------------------


class TestKimiMediaAdapter:
    """Kimi/Moonshot has no documented media-generation API."""

    def test_kimi_adapter_initialization(self):
        adapter = KimiMediaAdapter()
        assert adapter.PROVIDER_NAME == "kimi"
        assert "moonshot" in adapter.BASE_URL or "kimi" in adapter.BASE_URL

    @pytest.mark.asyncio
    async def test_kimi_image_unsupported(self):
        adapter = KimiMediaAdapter()
        result = await adapter.generate_image("a cat", "1:1")
        assert result["status"] == "unsupported"
        assert result["provider"] == "kimi"
        assert result["modality"] == "image"
        assert "not supported" in result["message"].lower() or "does not provide a documented" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_kimi_video_unsupported(self):
        adapter = KimiMediaAdapter()
        result = await adapter.generate_video("https://example.com/img.png", "animate")
        assert result["status"] == "unsupported"
        assert result["provider"] == "kimi"
        assert result["modality"] == "video"

    @pytest.mark.asyncio
    async def test_kimi_tts_unsupported(self):
        adapter = KimiMediaAdapter()
        result = await adapter.synthesize_tts("hello world", "voice-1")
        assert result["status"] == "unsupported"
        assert result["provider"] == "kimi"
        assert result["modality"] == "tts"

    @pytest.mark.asyncio
    async def test_kimi_audio_unsupported(self):
        adapter = KimiMediaAdapter()
        result = await adapter.generate_audio("ambient sound", 5.0)
        assert result["status"] == "unsupported"
        assert result["provider"] == "kimi"
        assert result["modality"] == "audio"


# ---------------------------------------------------------------------------
# GLM adapter tests
# ---------------------------------------------------------------------------


class TestGLMMediaAdapter:
    """GLM/Z.AI has documented image and video APIs; no TTS/audio generation."""

    def test_glm_adapter_initialization(self):
        adapter = GLMMediaAdapter(api_key="test-key", base_url="https://api.z.ai/api/paas/v4")
        assert adapter.PROVIDER_NAME == "glm"
        assert adapter.api_key == "test-key"
        assert "z.ai" in adapter.base_url

    def test_glm_adapter_api_key_from_settings(self, monkeypatch):
        monkeypatch.setenv("Z_AI_API_KEY", "zai-secret-key")
        monkeypatch.delenv("ZAI_API_KEY", raising=False)
        settings = Settings()
        adapter = GLMMediaAdapter()
        # The adapter should resolve from settings lazily
        # (we test the property, which reads from settings module)
        with patch("app.core.services.glm_media_adapter.settings", settings):
            assert adapter.api_key == "zai-secret-key"

    def test_glm_adapter_no_api_key_raises(self):
        adapter = GLMMediaAdapter(api_key=None, base_url="https://api.z.ai/api/paas/v4")
        with patch("app.core.services.glm_media_adapter.settings") as mock_settings:
            mock_settings.z_ai_api_key = None
            with pytest.raises(RuntimeError, match="Z_AI_API_KEY"):
                _ = adapter.api_key

    @pytest.mark.asyncio
    async def test_glm_tts_unsupported(self):
        adapter = GLMMediaAdapter(api_key="test-key", base_url="https://api.z.ai/api/paas/v4")
        result = await adapter.synthesize_tts("hello", "voice-1")
        assert result["status"] == "unsupported"
        assert result["provider"] == "glm"
        assert result["modality"] == "tts"
        assert "TTS" in result["message"]

    @pytest.mark.asyncio
    async def test_glm_audio_unsupported(self):
        adapter = GLMMediaAdapter(api_key="test-key", base_url="https://api.z.ai/api/paas/v4")
        result = await adapter.generate_audio("ambient", 5.0)
        assert result["status"] == "unsupported"
        assert result["provider"] == "glm"
        assert result["modality"] == "audio"
        assert "audio-generation" in result["message"].lower() or "ASR" in result["message"]

    @pytest.mark.asyncio
    async def test_glm_image_sync_success(self):
        """Test sync image generation with cogview-4-250304 (non-async path)."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"url": "https://cdn.z.ai/images/test-123.png"}],
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        adapter = GLMMediaAdapter(
            api_key="test-key",
            base_url="https://api.z.ai/api/paas/v4",
            http_client=mock_client,
        )
        result = await adapter.generate_image(
            prompt="a cute cat",
            aspect_ratio="1:1",
            model_id="cogview-4-250304",
            quality="standard",
        )

        assert result["status"] == "success"
        assert result["image_url"] == "https://cdn.z.ai/images/test-123.png"
        assert result["metadata"]["provider"] == "glm"
        assert result["metadata"]["model"] == "cogview-4-250304"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_glm_image_async_success(self):
        """Test async image generation with glm-image (async polling path)."""
        # First call: create async task
        create_response = MagicMock()
        create_response.raise_for_status = MagicMock()
        create_response.json.return_value = {"id": "task-abc-123"}

        # Polling responses: first PROCESSING, then SUCCESS
        poll_processing = MagicMock()
        poll_processing.raise_for_status = MagicMock()
        poll_processing.json.return_value = {"task_status": "PROCESSING", "id": "task-abc-123"}

        poll_success = MagicMock()
        poll_success.raise_for_status = MagicMock()
        poll_success.json.return_value = {
            "task_status": "SUCCESS",
            "id": "task-abc-123",
            "image_result": [{"url": "https://cdn.z.ai/images/async-result.png"}],
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=create_response)
        mock_client.get = AsyncMock(side_effect=[poll_processing, poll_success])

        adapter = GLMMediaAdapter(
            api_key="test-key",
            base_url="https://api.z.ai/api/paas/v4",
            http_client=mock_client,
        )

        # Patch the sleep to avoid real delays
        with patch("app.core.services.glm_media_adapter.asyncio.sleep", new=AsyncMock()):
            result = await adapter.generate_image(
                prompt="a cute kitten",
                aspect_ratio="1:1",
                model_id="glm-image",
                quality="hd",
            )

        assert result["status"] == "success"
        assert result["image_url"] == "https://cdn.z.ai/images/async-result.png"
        assert result["metadata"]["task_id"] == "task-abc-123"
        assert result["metadata"]["provider"] == "glm"
        assert result["metadata"]["model"] == "glm-image"

    @pytest.mark.asyncio
    async def test_glm_video_async_success(self):
        """Test async video generation with cogvideox-3."""
        create_response = MagicMock()
        create_response.raise_for_status = MagicMock()
        create_response.json.return_value = {"id": "video-task-456"}

        poll_success = MagicMock()
        poll_success.raise_for_status = MagicMock()
        poll_success.json.return_value = {
            "task_status": "SUCCESS",
            "id": "video-task-456",
            "video_result": [{"url": "https://cdn.z.ai/videos/result.mp4"}],
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=create_response)
        mock_client.get = AsyncMock(return_value=poll_success)

        adapter = GLMMediaAdapter(
            api_key="test-key",
            base_url="https://api.z.ai/api/paas/v4",
            http_client=mock_client,
        )

        with patch("app.core.services.glm_media_adapter.asyncio.sleep", new=AsyncMock()):
            result = await adapter.generate_video(
                image_url="https://example.com/image.png",
                prompt="make the picture move",
                model_id="cogvideox-3",
            )

        assert result["status"] == "success"
        assert result["video_url"] == "https://cdn.z.ai/videos/result.mp4"
        assert result["metadata"]["task_id"] == "video-task-456"
        assert result["metadata"]["provider"] == "glm"
        assert result["metadata"]["model"] == "cogvideox-3"

    @pytest.mark.asyncio
    async def test_glm_image_no_url_returns_error(self):
        """When the Z.AI response has no image URL, return error status."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        adapter = GLMMediaAdapter(
            api_key="test-key",
            base_url="https://api.z.ai/api/paas/v4",
            http_client=mock_client,
        )
        result = await adapter.generate_image(
            prompt="test",
            aspect_ratio="1:1",
            model_id="cogview-4-250304",
        )

        assert result["status"] == "error"
        assert "No image URL" in result["error"] or "error" in result.get("error", "").lower()

    def test_glm_aspect_ratio_mapping(self):
        adapter = GLMMediaAdapter(api_key="test-key", base_url="https://api.z.ai/api/paas/v4")
        assert adapter._aspect_ratio_to_size("1:1") == "1280x1280"
        assert adapter._aspect_ratio_to_size("16:9") == "1728x960"
        assert adapter._aspect_ratio_to_size("9:16") == "960x1728"
        assert adapter._aspect_ratio_to_size("unknown") == "1280x1280"


# ---------------------------------------------------------------------------
# Media router SUPPORTED_PROVIDERS tests
# ---------------------------------------------------------------------------


class TestMediaRouterProviders:
    """Verify KAN-447 additive providers are in SUPPORTED_PROVIDERS."""

    def test_glm_in_image_providers(self):
        router = MediaRouter()
        assert "glm" in router.SUPPORTED_PROVIDERS["image"]

    def test_glm_in_video_providers(self):
        router = MediaRouter()
        assert "glm" in router.SUPPORTED_PROVIDERS["video"]

    def test_kimi_in_audio_providers(self):
        router = MediaRouter()
        assert "kimi" in router.SUPPORTED_PROVIDERS["audio"]

    def test_kimi_in_tts_providers(self):
        router = MediaRouter()
        assert "kimi" in router.SUPPORTED_PROVIDERS["tts"]

    def test_glm_in_audio_providers(self):
        router = MediaRouter()
        assert "glm" in router.SUPPORTED_PROVIDERS["audio"]

    def test_glm_in_tts_providers(self):
        router = MediaRouter()
        assert "glm" in router.SUPPORTED_PROVIDERS["tts"]

    def test_existing_providers_not_removed(self):
        router = MediaRouter()
        # Ensure existing providers are still present
        assert "modelslab" in router.SUPPORTED_PROVIDERS["image"]
        assert "piapi" in router.SUPPORTED_PROVIDERS["image"]
        assert "elevenlabs" in router.SUPPORTED_PROVIDERS["audio"]


# ---------------------------------------------------------------------------
# Model config ladder tests
# ---------------------------------------------------------------------------


class TestModelConfigLadders:
    """Verify GLM entries are additively added to tier ladders."""

    def test_image_free_has_glm_fallback(self):
        from app.core.model_config import IMAGE_MODEL_CONFIG, ModelTier

        config = IMAGE_MODEL_CONFIG[ModelTier.FREE]
        models = config.models
        assert "glm/glm-image" in models
        # Ensure existing entries are not reordered
        assert models[0] == "seedream-t2i"
        assert models[1] == "seedream-4"

    def test_image_enterprise_has_glm_fallback(self):
        from app.core.model_config import IMAGE_MODEL_CONFIG, ModelTier

        config = IMAGE_MODEL_CONFIG[ModelTier.ENTERPRISE]
        models = config.models
        assert "glm/glm-image" in models
        # Existing entries preserved
        assert models[0] == "nano-banana-pro"

    def test_video_free_has_glm_fallback(self):
        from app.core.model_config import VIDEO_MODEL_CONFIG, ModelTier

        config = VIDEO_MODEL_CONFIG[ModelTier.FREE]
        models = config.models
        assert "glm/cogvideox-3" in models
        # Existing order preserved
        assert models[0] == "wan2.5-i2v"

    def test_video_standard_has_glm_fallback(self):
        from app.core.model_config import VIDEO_MODEL_CONFIG, ModelTier

        config = VIDEO_MODEL_CONFIG[ModelTier.STANDARD]
        models = config.models
        assert "glm/cogvideox-3" in models
        assert models[0] == "omni-human-1.5"

    def test_video_enterprise_has_glm_fallback(self):
        from app.core.model_config import VIDEO_MODEL_CONFIG, ModelTier

        config = VIDEO_MODEL_CONFIG[ModelTier.ENTERPRISE]
        models = config.models
        assert "glm/cogvideox-3" in models
        assert models[0] == "omni-human-1.5"

    def test_no_existing_image_primary_changed(self):
        """Verify no existing primary image model was changed."""
        from app.core.model_config import IMAGE_MODEL_CONFIG, ModelTier

        expected_primaries = {
            ModelTier.FREE: "seedream-t2i",
            ModelTier.BASIC: "seedream-4",
            ModelTier.STANDARD: "imagen-4",
            ModelTier.PREMIUM: "nano-banana-t2i",
            ModelTier.PRO: "seedream-4.5",
            ModelTier.PROFESSIONAL: "seedream-4.5",
            ModelTier.ENTERPRISE: "nano-banana-pro",
        }
        for tier, expected in expected_primaries.items():
            assert IMAGE_MODEL_CONFIG[tier].primary == expected, f"{tier}: {IMAGE_MODEL_CONFIG[tier].primary} != {expected}"

    def test_no_existing_video_primary_changed(self):
        """Verify no existing primary video model was changed."""
        from app.core.model_config import VIDEO_MODEL_CONFIG, ModelTier

        expected_primaries = {
            ModelTier.FREE: "wan2.5-i2v",
            ModelTier.BASIC: "wan2.6-i2v",
            ModelTier.STANDARD: "omni-human-1.5",
            ModelTier.PREMIUM: "omni-human",
            ModelTier.PRO: "omni-human",
            ModelTier.PROFESSIONAL: "omni-human",
            ModelTier.ENTERPRISE: "omni-human-1.5",
        }
        for tier, expected in expected_primaries.items():
            assert VIDEO_MODEL_CONFIG[tier].primary == expected, f"{tier}: {VIDEO_MODEL_CONFIG[tier].primary} != {expected}"


# ---------------------------------------------------------------------------
# ProviderUnsupportedResult tests
# ---------------------------------------------------------------------------


class TestProviderUnsupportedResult:
    """Test the unsupported-result dataclass."""

    def test_to_dict(self):
        result = ProviderUnsupportedResult(
            provider="kimi",
            modality="image",
            message="No documented API",
        )
        d = result.to_dict()
        assert d["status"] == "unsupported"
        assert d["provider"] == "kimi"
        assert d["modality"] == "image"
        assert d["message"] == "No documented API"

    def test_defaults(self):
        result = ProviderUnsupportedResult()
        assert result.status == "unsupported"
        assert result.provider == "glm"  # default in glm_media_adapter
        assert result.modality == ""