from unittest.mock import AsyncMock, Mock

import pytest

from app.core.services.piapi_audio_adapter import PiAPIAudioAdapter


class FailingTTSRouter:
    async def synthesize(self, **kwargs):
        return {"status": "error", "error": "elevenlabs unavailable"}


class FailingModelsLabAudioService:
    api_key = "modelslab-test-key"

    async def generate_tts_audio(self, **kwargs):
        raise RuntimeError("modelslab unavailable")

    async def generate_sound_effect(self, **kwargs):
        raise RuntimeError("modelslab unavailable")

    async def generate_background_music(self, **kwargs):
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
            "url": f"https://cdn.piapi.ai/{task_type}.mp3",
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
        return_value="http://localhost:9000/litinkai-staging/users/system/audio/generated.mp3"
    )
    storage.presigned_url = Mock(
        side_effect=lambda path, expiration=3600: f"http://localhost:9000/litinkai-staging/{path}"
    )
    return storage


@pytest.mark.asyncio
async def test_tts_modelslab_and_elevenlabs_failures_fall_back_to_piapi():
    piapi = SuccessfulPiAPIClient()
    storage = _storage()
    adapter = PiAPIAudioAdapter(
        piapi=piapi,
        tts_router=FailingTTSRouter(),
        modelslab_service=FailingModelsLabAudioService(),
        storage_service=storage,
    )

    result = await adapter.synthesize_text(
        text="A quiet line of dialogue.",
        voice_id="voice-123",
        user_tier="standard",
        speed=1.1,
        emotion="calm",
    )

    assert result["status"] == "success"
    assert result["canonical_url"].startswith("http://localhost:9000/litinkai-staging/")
    assert result["provider_url"] == "https://cdn.piapi.ai/text2audio.mp3"
    assert result["metadata"]["provider"] == "piapi"
    assert result["metadata"]["model"] == "f5tts"
    assert any(
        model.startswith("piapi/") for model in result["metadata"]["model_ladder"]
    )
    assert piapi.calls[-1]["task_type"] == "text2audio"
    assert piapi.calls[-1]["input"] == {
        "text": "A quiet line of dialogue.",
        "voice_id": "voice-123",
        "speed": 1.1,
        "emotion": "calm",
    }
    storage.persist_from_url.assert_awaited_once()


@pytest.mark.asyncio
async def test_sfx_modelslab_failure_falls_back_to_piapi():
    piapi = SuccessfulPiAPIClient()
    adapter = PiAPIAudioAdapter(
        piapi=piapi,
        modelslab_service=FailingModelsLabAudioService(),
        storage_service=_storage(),
    )

    result = await adapter.generate_sound_effect(
        prompt="distant thunder over an empty street",
        duration=4.5,
        intensity="medium",
        user_tier="standard",
    )

    assert result["status"] == "success"
    assert result["provider_url"] == "https://cdn.piapi.ai/sound-effect.mp3"
    assert result["metadata"]["provider"] == "piapi"
    assert result["metadata"]["model"] == "fx-musicgen"
    assert piapi.calls[-1]["task_type"] == "sound-effect"
    assert piapi.calls[-1]["input"] == {
        "prompt": "distant thunder over an empty street",
        "duration": 4.5,
        "intensity": "medium",
    }


@pytest.mark.asyncio
async def test_music_modelslab_failure_falls_back_to_piapi():
    piapi = SuccessfulPiAPIClient()
    adapter = PiAPIAudioAdapter(
        piapi=piapi,
        modelslab_service=FailingModelsLabAudioService(),
        storage_service=_storage(),
    )

    result = await adapter.generate_music(
        prompt="tense orchestral trailer cue",
        duration=30,
        user_tier="standard",
        style="cinematic",
    )

    assert result["status"] == "success"
    assert result["provider_url"] == "https://cdn.piapi.ai/music.mp3"
    assert result["metadata"]["provider"] == "piapi"
    assert result["metadata"]["model"] == "ace-step"
    assert piapi.calls[-1]["task_type"] == "music"
    assert piapi.calls[-1]["input"] == {
        "prompt": "tense orchestral trailer cue",
        "duration": 30,
        "style": "cinematic",
    }


@pytest.mark.asyncio
async def test_all_audio_providers_fail_returns_error_and_does_not_charge():
    charge_credits = Mock()
    adapter = PiAPIAudioAdapter(
        piapi=FailingPiAPIClient(),
        tts_router=FailingTTSRouter(),
        modelslab_service=FailingModelsLabAudioService(),
        storage_service=_storage(),
        charge_credits=charge_credits,
    )

    result = await adapter.synthesize_text(
        text="This line cannot be synthesized.",
        voice_id="voice-123",
        user_tier="standard",
    )

    assert result["status"] == "error"
    assert result["attempted_models"]
    charge_credits.assert_not_called()
