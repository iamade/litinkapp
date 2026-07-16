import logging

import pytest

from app.core.config import settings
from app.core.services.modelslab_v7_image import ModelsLabV7ImageService
from app.core.services.modelslab_v7_video import ModelsLabV7VideoService


FAKE_KEY = "modelslab-test-key-ABC123"


class FakeResponse:
    def __init__(self, payload, status=200, text=None):
        self.payload = payload
        self.status = status
        self._text = text or str(payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self.payload

    async def text(self):
        return self._text


class FakeClientSession:
    def __init__(self, responses=None):
        self.responses = list(responses or [])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json=None, headers=None, timeout=None):
        if self.responses:
            return self.responses.pop(0)
        if "outpaint" in url:
            return FakeResponse(
                {
                    "status": "success",
                    "output": ["https://cdn.modelslab.com/expanded.png"],
                }
            )
        return FakeResponse(
            {
                "status": "success",
                "output": ["https://cdn.modelslab.com/generated.mp4"],
            }
        )


@pytest.fixture(autouse=True)
def fake_modelslab_settings(monkeypatch):
    monkeypatch.setattr(settings, "MODELSLAB_API_KEY", FAKE_KEY)
    monkeypatch.setattr(settings, "MODELSLAB_BASE_URL", "https://modelslab.test/api/v7")
    monkeypatch.setattr(settings, "MODELSLAB_V6_BASE_URL", "https://modelslab.test/api/v6")


@pytest.mark.asyncio
async def test_modelslab_payload_logs_and_errors_redact_api_key(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        "app.core.services.modelslab_v7_image.aiohttp.ClientSession",
        lambda: FakeClientSession(),
    )
    monkeypatch.setattr(
        "app.core.services.modelslab_v7_video.aiohttp.ClientSession",
        lambda: FakeClientSession(),
    )

    image_service = ModelsLabV7ImageService()
    video_service = ModelsLabV7VideoService()

    image_result = await image_service.expand_image(
        "https://cdn.example.com/input.png",
        "16:9",
        prompt="extend the scene",
    )
    video_result = await video_service.generate_image_to_video(
        image_url="https://cdn.example.com/input.png",
        prompt="cinematic motion",
        model_id="wan2.6-i2v",
    )
    lipsync_result = await video_service.generate_lip_sync(
        video_url="https://cdn.example.com/input.mp4",
        audio_url="https://cdn.example.com/input.mp3",
    )

    error_responses = [
        FakeResponse(
            {"status": "error"},
            status=500,
            text=f"upstream echoed {FAKE_KEY}",
        ),
        FakeResponse(
            {"status": "error"},
            status=500,
            text=f"upstream echoed {FAKE_KEY}",
        ),
    ]
    monkeypatch.setattr(
        "app.core.services.modelslab_v7_video.aiohttp.ClientSession",
        lambda: FakeClientSession(error_responses),
    )
    with pytest.raises(Exception) as exc_info:
        await video_service.generate_image_to_video(
            image_url="https://cdn.example.com/input.png",
            prompt="cinematic motion",
            model_id="wan2.6-i2v",
        )

    all_visible_text = "\n".join(
        [
            caplog.text,
            str(image_result),
            str(video_result),
            str(lipsync_result),
            str(exc_info.value),
        ]
    )
    assert FAKE_KEY not in all_visible_text
    assert "***" in all_visible_text
    assert "[IMAGE EXPAND] Payload:" in caplog.text
