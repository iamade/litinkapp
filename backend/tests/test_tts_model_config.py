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


def test_chapter_audio_narrator_character_path_uses_scoped_modelslab_chain():
    assert audio_tasks.CHAPTER_AUDIO_TTS_MODEL_CHAIN == EXPECTED_CHAPTER_AUDIO_TTS_CHAIN
    assert not any(
        blocked in model
        for model in audio_tasks.CHAPTER_AUDIO_TTS_MODEL_CHAIN
        for blocked in DISALLOWED_CHAPTER_AUDIO_PROVIDERS
    )

    source = inspect.getsource(audio_tasks.generate_chapter_audio_task.run)
    assert 'use_chapter_tts = audio_type in ["narrator", "character"]' in source
    assert "generate_tts_audio" in source
    assert "model_id=model_id" in source


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


def test_chapter_audio_tts_uses_modelslab_model_ids_without_direct_elevenlabs(monkeypatch):
    import contextlib
    import uuid
    from types import SimpleNamespace

    from app.core.services import storage as storage_module

    chapter_id = uuid.uuid4()
    record_id = uuid.uuid4()
    audio_record = SimpleNamespace(chapter_id=chapter_id)
    model_calls = []
    persisted = []

    class _Result:
        def first(self):
            return audio_record

    class _Session:
        async def exec(self, statement):
            return _Result()

        def add(self, record):
            self.record = record

        async def commit(self):
            pass

    @contextlib.asynccontextmanager
    async def fake_session_scope():
        yield _Session()

    class _ModelsLabService:
        async def generate_tts_audio(self, **kwargs):
            model_calls.append(kwargs)
            return {
                "status": "success",
                "audio_url": "https://modelslab.example/audio.mp3",
                "audio_time": 1.25,
            }

    class _Storage:
        async def persist_from_url(self, url, path, content_type=None):
            persisted.append((url, path, content_type))
            return "s3://bucket/chapter-audio.mp3"

    def fail_direct_elevenlabs(*args, **kwargs):
        raise AssertionError("chapter TTS must not instantiate direct ElevenLabsService")

    monkeypatch.setattr(audio_tasks, "session_scope", fake_session_scope)
    monkeypatch.setattr(audio_tasks, "ModelsLabV7AudioService", _ModelsLabService)
    monkeypatch.setattr(audio_tasks, "ElevenLabsService", fail_direct_elevenlabs)
    monkeypatch.setattr(storage_module, "get_storage_service", lambda: _Storage())
    monkeypatch.setattr(
        storage_module.S3StorageService,
        "build_media_path",
        staticmethod(lambda **kwargs: "audio/generated.mp3"),
    )

    result = audio_tasks.generate_chapter_audio_task.run(
        audio_type="narrator",
        text_content="Hello from ModelsLab",
        user_id=str(uuid.uuid4()),
        chapter_id=str(chapter_id),
        scene_number=1,
        voice_id="voice-123",
        record_id=str(record_id),
    )

    assert result["status"] == "success"
    assert [call["model_id"] for call in model_calls] == ["eleven_turbo_v2"]
    assert model_calls[0]["voice_id"] == "voice-123"
    assert persisted == [
        ("https://modelslab.example/audio.mp3", "audio/generated.mp3", "audio/mpeg")
    ]
    assert audio_record.status == "completed"
    assert audio_record.audio_url == "s3://bucket/chapter-audio.mp3"
    assert audio_record.model_id == "eleven_turbo_v2"
    assert audio_record.audio_metadata["service_used"] == "modelslab_v7"


def test_chapter_audio_tts_falls_back_only_across_modelslab_eleven_model_ids(monkeypatch):
    import contextlib
    import uuid
    from types import SimpleNamespace

    from app.core.services import storage as storage_module

    chapter_id = uuid.uuid4()
    audio_record = SimpleNamespace(chapter_id=chapter_id)
    model_calls = []

    class _Result:
        def first(self):
            return audio_record

    class _Session:
        async def exec(self, statement):
            return _Result()

        def add(self, record):
            pass

        async def commit(self):
            pass

    @contextlib.asynccontextmanager
    async def fake_session_scope():
        yield _Session()

    class _ModelsLabService:
        async def generate_tts_audio(self, **kwargs):
            model_calls.append(kwargs["model_id"])
            if kwargs["model_id"] == "eleven_english_v1":
                return {
                    "status": "success",
                    "audio_url": "https://cdn.example/fallback.mp3",
                }
            return {"status": "error", "error": "unsupported"}

    class _Storage:
        async def persist_from_url(self, url, path, content_type=None):
            return "s3://bucket/fallback.mp3"

    monkeypatch.setattr(audio_tasks, "session_scope", fake_session_scope)
    monkeypatch.setattr(audio_tasks, "ModelsLabV7AudioService", _ModelsLabService)
    monkeypatch.setattr(storage_module, "get_storage_service", lambda: _Storage())
    monkeypatch.setattr(
        storage_module.S3StorageService,
        "build_media_path",
        staticmethod(lambda **kwargs: "audio/fallback.mp3"),
    )

    result = audio_tasks.generate_chapter_audio_task.run(
        audio_type="character",
        text_content="Fallback through ModelsLab",
        user_id=str(uuid.uuid4()),
        chapter_id=str(chapter_id),
        scene_number=1,
        record_id=str(uuid.uuid4()),
    )

    assert result["status"] == "success"
    assert model_calls == [
        "eleven_turbo_v2",
        "eleven_multilingual_v2",
        "eleven_english_v1",
    ]
    assert audio_record.model_id == "eleven_english_v1"


def test_chapter_audio_tts_source_bypasses_router_and_direct_elevenlabs():
    source = inspect.getsource(audio_tasks.generate_chapter_audio_task.run)
    tts_branch = source.split('if use_chapter_tts:', 1)[1].split('else:', 1)[0]
    assert "ModelsLabV7AudioService()" in tts_branch
    assert "generate_tts_audio" in tts_branch
    assert "tts_router.synthesize" not in tts_branch
    assert "ElevenLabsService()" not in tts_branch
