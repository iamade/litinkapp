import ast
from pathlib import Path

import pytest

from app.tasks import tts_router_adapter


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


def _audio_tasks_source() -> str:
    for path in (
        Path("backend/app/tasks/audio_tasks.py"),
        Path("app/tasks/audio_tasks.py"),
        Path("/app/app/tasks/audio_tasks.py"),
    ):
        if path.exists():
            return path.read_text()
    raise FileNotFoundError("audio_tasks.py not found in known test locations")


def test_narrator_and_character_paths_use_tts_router_adapter():
    source = _audio_tasks_source()
    tree = ast.parse(source)

    functions = {node.name: ast.get_source_segment(source, node) for node in tree.body if isinstance(node, ast.AsyncFunctionDef)}

    narrator_source = functions["generate_narrator_audio"]
    character_source = functions["generate_character_audio"]

    assert "_generate_tts_via_router" in narrator_source
    assert "_generate_tts_via_router" in character_source
    assert "text=segment[\"text\"]" in narrator_source
    assert "text=dialogue[\"text\"]" in character_source
    assert "model=\"elevenlabs/eleven_multilingual_v2\"" in narrator_source
    assert "model=\"elevenlabs/eleven_multilingual_v2\"" in character_source

    # The KAN-175 first slice must remove direct TTS calls from these paths.
    assert "generate_tts_audio(" not in narrator_source
    assert "generate_tts_audio(" not in character_source
    assert "ElevenLabsService()" not in narrator_source
    assert "ElevenLabsService()" not in character_source


def test_non_tts_music_and_sound_effect_paths_remain_on_modelslab_service():
    source = _audio_tasks_source()

    # Non-TTS paths should remain on ModelsLabV7AudioService and sound-effect generation.
    assert "if audio_type == \"music\":" in source
    assert "result = await audio_service.generate_sound_effect(" in source
    assert "# Use ModelsLab for non-TTS audio types" in source
