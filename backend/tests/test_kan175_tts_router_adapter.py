from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.services import storage as storage_module
from app.tasks import audio_tasks, tts_router_adapter


class _NoopSession:
    async def exec(self, *_args, **_kwargs):
        return SimpleNamespace(first=lambda: None)

    def add(self, _record):
        return None

    async def commit(self):
        return None


@asynccontextmanager
async def _noop_session_scope():
    yield _NoopSession()


class _FakeStorage:
    async def persist_from_url(self, url, _path, content_type=None):
        assert content_type == "audio/mpeg"
        return f"s3://test/{url.rsplit('/', 1)[-1]}"


@pytest.mark.asyncio
async def test_generate_tts_via_router_maps_success(monkeypatch):
    calls = []

    async def fake_synthesize(**kwargs):
        calls.append(kwargs)
        return {
            "status": "success",
            "provider": "elevenlabs",
            "model": "eleven_multilingual_v2",
            "audio_url": "https://cdn.example/audio.mp3",
            "duration_seconds": 12.5,
            "metadata": {"provider_audio_url": "https://cdn.example/audio.mp3"},
        }

    monkeypatch.setattr(tts_router_adapter.tts_router, "synthesize", fake_synthesize)

    result = await tts_router_adapter._generate_tts_via_router(
        user_id="user-1",
        user_tier="standard",
        text="Narrator line",
        voice_id="voice-1",
        model="elevenlabs/eleven_multilingual_v2",
        speed=1.0,
    )

    assert calls == [
        {
            "text": "Narrator line",
            "user_tier": "standard",
            "voice_id": "voice-1",
            "model": "elevenlabs/eleven_multilingual_v2",
            "model_chain": None,
            "style": 0.0,
            "user_id": "user-1",
            "speed": 1.0,
        }
    ]
    assert result == {
        "status": "success",
        "audio_url": "https://cdn.example/audio.mp3",
        "audio_time": 12.5,
        "model_used": "eleven_multilingual_v2",
        "service": "elevenlabs",
        "meta": {"provider_audio_url": "https://cdn.example/audio.mp3"},
        "error": None,
    }


@pytest.mark.asyncio
async def test_generate_tts_via_router_maps_failure(monkeypatch):
    async def fake_synthesize(**kwargs):
        raise RuntimeError("router unavailable")

    monkeypatch.setattr(tts_router_adapter.tts_router, "synthesize", fake_synthesize)

    result = await tts_router_adapter._generate_tts_via_router(
        user_id="user-1",
        user_tier="free",
        text="Character line",
        voice_id="voice-2",
    )

    assert result == {
        "status": "error",
        "error": "router unavailable",
        "service": "tts_router",
    }


@pytest.mark.asyncio
async def test_generate_tts_via_router_forwards_full_adapter_contract(monkeypatch):
    calls = []

    async def fake_synthesize(**kwargs):
        calls.append(kwargs)
        return {
            "status": "success",
            "provider": "fallback-provider",
            "model": "fallback-model",
            "audio_url": "https://cdn.example/fallback.mp3",
            "duration_seconds": 3.25,
            "metadata": {"trace": "router-contract"},
        }

    monkeypatch.setattr(tts_router_adapter.tts_router, "synthesize", fake_synthesize)

    result = await tts_router_adapter._generate_tts_via_router(
        user_id="user-2",
        user_tier="premium",
        text="Character line",
        voice_id="voice-2",
        model_chain=["elevenlabs/eleven_turbo_v2", "elevenlabs/eleven_multilingual_v2"],
        style=0.35,
        speed=0.9,
        stability=0.6,
    )

    assert calls == [
        {
            "text": "Character line",
            "user_tier": "premium",
            "voice_id": "voice-2",
            "model": None,
            "model_chain": [
                "elevenlabs/eleven_turbo_v2",
                "elevenlabs/eleven_multilingual_v2",
            ],
            "style": 0.35,
            "user_id": "user-2",
            "speed": 0.9,
            "stability": 0.6,
        }
    ]
    assert result == {
        "status": "success",
        "audio_url": "https://cdn.example/fallback.mp3",
        "audio_time": 3.25,
        "model_used": "fallback-model",
        "service": "fallback-provider",
        "meta": {"trace": "router-contract"},
        "error": None,
    }


def test_non_tts_music_and_sound_effect_paths_use_modelslab_contract(monkeypatch):
    services = []

    class FakeModelsLabService:
        def __init__(self):
            self.calls = []

        async def generate_sound_effect(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "status": "success",
                "audio_url": "https://cdn.example/non-tts.mp3",
                "audio_time": kwargs["duration"],
                "model_used": "modelslab-v7-test",
            }

    def fake_modelslab_factory():
        service = FakeModelsLabService()
        services.append(service)
        return service

    monkeypatch.setattr(audio_tasks, "session_scope", _noop_session_scope)
    monkeypatch.setattr(audio_tasks, "ModelsLabV7AudioService", fake_modelslab_factory)
    monkeypatch.setattr(storage_module, "get_storage_service", lambda: _FakeStorage())

    common = {
        "user_id": str(uuid4()),
        "chapter_id": str(uuid4()),
        "scene_number": 1,
        "record_id": None,
    }

    music_result = audio_tasks.generate_chapter_audio_task.run(
        audio_type="music",
        text_content="tense orchestral bed",
        **common,
    )
    sfx_result = audio_tasks.generate_chapter_audio_task.run(
        audio_type="sound_effect",
        text_content="door slam",
        **common,
    )

    assert music_result["status"] == "success"
    assert sfx_result["status"] == "success"
    assert services[0].calls == [
        {"description": "tense orchestral bed", "duration": 30.0}
    ]
    assert services[1].calls == [{"description": "door slam", "duration": 10.0}]
