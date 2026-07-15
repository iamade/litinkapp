from unittest.mock import AsyncMock, Mock

import pytest

from app.core.services.piapi_video_adapter import PiAPIVideoAdapter


class FailingModelsLabVideoService:
    async def generate_image_to_video(self, **kwargs):
        raise RuntimeError("modelslab unavailable")

    async def generate_lip_sync(self, **kwargs):
        raise RuntimeError("modelslab unavailable")


class SuccessfulPiAPIClient:
    def __init__(self):
        self.calls = []
        self.api_key = "piapi-test-key"

    async def create_and_poll(self, **kwargs):
        self.calls.append(kwargs)
        task_type = kwargs["task_type"]
        return {
            "status": "success",
            "url": f"https://cdn.piapi.ai/{task_type}.mp4",
            "metadata": {"task_id": f"task-{task_type}"},
            "error": None,
        }


class FailingPiAPIClient:
    api_key = "piapi-test-key"

    async def create_and_poll(self, **kwargs):
        raise RuntimeError("piapi unavailable")


def _storage():
    storage = Mock()
    storage.persist_from_url = AsyncMock(
        return_value="http://localhost:9000/litinkai-staging/users/system/videos/generated.mp4"
    )
    storage.presigned_url = Mock(
        side_effect=lambda path, expiration=3600: f"http://localhost:9000/litinkai-staging/{path}"
    )
    return storage


@pytest.mark.asyncio
async def test_image_to_video_modelslab_failure_falls_back_to_piapi():
    piapi = SuccessfulPiAPIClient()
    storage = _storage()
    adapter = PiAPIVideoAdapter(
        piapi=piapi,
        modelslab_service=FailingModelsLabVideoService(),
        storage_service=storage,
    )

    result = await adapter.generate_image_to_video(
        image_url="users/test/input.png",
        prompt="a cinematic pan across a book cover",
        user_tier="free",
        duration=5,
        aspect_ratio="16:9",
    )

    assert result["status"] == "success"
    assert result["canonical_url"].startswith("http://localhost:9000/litinkai-staging/")
    assert result["provider_url"] == "https://cdn.piapi.ai/image2video.mp4"
    assert result["metadata"]["provider"] == "piapi"
    assert piapi.calls[-1]["task_type"] == "image2video"
    assert piapi.calls[-1]["input"]["image_url"].startswith(
        "http://localhost:9000/litinkai-staging/"
    )
    storage.persist_from_url.assert_awaited_once()


@pytest.mark.asyncio
async def test_lip_sync_modelslab_failure_falls_back_to_piapi():
    piapi = SuccessfulPiAPIClient()
    storage = _storage()
    adapter = PiAPIVideoAdapter(
        piapi=piapi,
        modelslab_service=FailingModelsLabVideoService(),
        storage_service=storage,
    )

    result = await adapter.generate_lip_sync(
        video_url="users/test/input.mp4",
        audio_url="users/test/input.mp3",
        user_tier="free",
    )

    assert result["status"] == "success"
    assert result["canonical_url"].startswith("http://localhost:9000/litinkai-staging/")
    assert result["provider_url"] == "https://cdn.piapi.ai/lipsync.mp4"
    assert result["metadata"]["provider"] == "piapi"
    assert piapi.calls[-1]["task_type"] == "lipsync"
    assert piapi.calls[-1]["input"]["video_url"].startswith(
        "http://localhost:9000/litinkai-staging/"
    )
    assert piapi.calls[-1]["input"]["audio_url"].startswith(
        "http://localhost:9000/litinkai-staging/"
    )


@pytest.mark.asyncio
async def test_all_video_providers_fail_returns_error_and_does_not_charge():
    charge_credits = Mock()
    adapter = PiAPIVideoAdapter(
        piapi=FailingPiAPIClient(),
        modelslab_service=FailingModelsLabVideoService(),
        storage_service=_storage(),
        charge_credits=charge_credits,
    )

    result = await adapter.generate_image_to_video(
        image_url="users/test/input.png",
        prompt="a cinematic pan across a book cover",
        user_tier="free",
    )

    assert result["status"] == "error"
    assert result["attempted_models"]
    charge_credits.assert_not_called()
