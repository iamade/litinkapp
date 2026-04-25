import inspect

import pytest

from app.core.model_config import ModelTier, get_model_config
from app.core.services.tts import router as tts_router_module
from app.core.services.tts.router import TTSRouter
from app.tasks import audio_tasks


EXPECTED_GLOBAL_TTS_CHAINS = {
    "free": ["elevenlabs/eleven_turbo_v2", "openai/tts-1", "google/text-to-speech"],
    "basic": ["elevenlabs/eleven_multilingual_v2", "openai/tts-1-hd", "google/text-to-speech"],
    "standard": [
        "elevenlabs/eleven_multilingual_v2",
        "openai/tts-1-hd",
        "google/text-to-speech",
        "fish-speech/default",
    ],
    "premium": [
        "elevenlabs/eleven_multilingual_v2",
        "openai/tts-1-hd",
        "google/text-to-speech",
        "fish-speech/default",
    ],
    "professional": [
        "elevenlabs/eleven_multilingual_v2",
        "openai/tts-1-hd",
        "fish-speech/default",
        "google/text-to-speech",
    ],
    "enterprise": [
        "elevenlabs/eleven_multilingual_v2",
        "openai/tts-1-hd",
        "fish-speech/default",
        "google/text-to-speech",
        "kokoro/default",
    ],
}

EXPECTED_CHAPTER_AUDIO_TTS_CHAIN = [
    "elevenlabs/eleven_turbo_v2",
    "elevenlabs/eleven_multilingual_v2",
    "elevenlabs/eleven_english_v1",
]


DISALLOWED_CHAPTER_AUDIO_PROVIDERS = (
    "google",
    "openai",
    "fish-speech",
    "kokoro",
)


def _configured_chain(config):
    return [
        model
        for model in (
            config.primary,
            config.fallback,
            config.fallback2,
            config.fallback3,
            config.fallback4,
        )
        if model
    ]


def test_global_tts_tier_config_preserves_broader_provider_fallbacks():
    for tier in ModelTier:
        config = get_model_config("tts", tier.value)
        assert config is not None
        assert _configured_chain(config) == EXPECTED_GLOBAL_TTS_CHAINS[tier.value]

    global_models = {
        model
        for chain in EXPECTED_GLOBAL_TTS_CHAINS.values()
        for model in chain
    }
    assert "openai/tts-1-hd" in global_models
    assert "google/text-to-speech" in global_models
    assert "fish-speech/default" in global_models
    assert "kokoro/default" in global_models


def test_chapter_audio_narrator_character_path_uses_elevenlabs_only_chain():
    assert audio_tasks.CHAPTER_AUDIO_TTS_MODEL_CHAIN == EXPECTED_CHAPTER_AUDIO_TTS_CHAIN
    assert not any(
        blocked in model
        for model in audio_tasks.CHAPTER_AUDIO_TTS_MODEL_CHAIN
        for blocked in DISALLOWED_CHAPTER_AUDIO_PROVIDERS
    )

    source = inspect.getsource(audio_tasks.generate_chapter_audio_task.run)
    assert 'use_tts_router = audio_type in ["narrator", "character"]' in source
    assert "model_chain=CHAPTER_AUDIO_TTS_MODEL_CHAIN" in source


@pytest.mark.asyncio
async def test_tts_router_model_chain_uses_scoped_fallback_list(monkeypatch):
    captured = {}

    async def fake_try_model_list_with_fallback(**kwargs):
        captured.update(kwargs)
        return {"status": "success", "audio_url": "https://cdn.example/audio.mp3"}

    monkeypatch.setattr(
        tts_router_module.fallback_manager,
        "try_model_list_with_fallback",
        fake_try_model_list_with_fallback,
    )

    router = TTSRouter()
    result = await router.synthesize(
        text="hello",
        user_tier="enterprise",
        voice_id="voice-1",
        model_chain=EXPECTED_CHAPTER_AUDIO_TTS_CHAIN,
    )

    assert result["status"] == "success"
    assert captured["models"] == EXPECTED_CHAPTER_AUDIO_TTS_CHAIN
    assert captured["model_param_name"] == "model"
    assert captured["service_type"] == "tts"
