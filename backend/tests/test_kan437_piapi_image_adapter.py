from unittest.mock import AsyncMock

import pytest

from app.core.services.piapi_image_adapter import PiAPIImageAdapter


class FailingModelsLabService:
    async def generate_image(self, **kwargs):
        raise RuntimeError("modelslab unavailable")


class FakePiAPIClient:
    def __init__(self):
        self.calls = []

    async def create_and_poll(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "status": "success",
            "url": "https://cdn.piapi.ai/generated.png",
            "metadata": {"task_id": "task-437"},
            "error": None,
        }


@pytest.mark.asyncio
async def test_modelslab_failure_falls_back_to_piapi_and_persists():
    piapi = FakePiAPIClient()
    storage = AsyncMock()
    storage.persist_from_url = AsyncMock(
        return_value="http://localhost:9000/litinkai-staging/users/system/images/generated.png"
    )
    adapter = PiAPIImageAdapter(
        piapi=piapi,
        modelslab_service=FailingModelsLabService(),
        storage_service=storage,
    )

    result = await adapter.generate(
        prompt="a cinematic book trailer still",
        aspect_ratio="16:9",
        user_tier="free",
    )

    assert result["status"] == "success"
    assert result["canonical_url"].startswith(
        "http://localhost:9000/litinkai-staging/"
    )
    assert result["provider_url"] == "https://cdn.piapi.ai/generated.png"
    assert result["metadata"]["provider"] == "piapi"
    assert result["metadata"]["model"] == "flux-schnell"
    assert piapi.calls[0]["model"] == "flux-schnell"
    storage.persist_from_url.assert_awaited_once()
