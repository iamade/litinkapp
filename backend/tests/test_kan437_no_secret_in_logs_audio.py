import logging

import pytest

from app.core.config import settings
from app.core.services.piapi_audio_adapter import PiAPIAudioAdapter


class SecretFailingTTSRouter:
    def __init__(self, secret: str):
        self.secret = secret

    async def synthesize(self, **kwargs):
        raise RuntimeError(f"elevenlabs failed with {self.secret}")


class SecretFailingModelsLabAudioService:
    def __init__(self, secret: str):
        self.api_key = secret

    async def generate_tts_audio(self, **kwargs):
        raise RuntimeError(f"modelslab failed with {self.api_key}")


class SecretFailingPiAPIClient:
    def __init__(self, secret: str):
        self.api_key = secret

    async def create_and_poll(self, **kwargs):
        raise RuntimeError(f"piapi failed with {self.api_key}")


@pytest.mark.asyncio
async def test_audio_adapter_redacts_provider_secrets_from_logs_and_errors(
    monkeypatch, caplog
):
    piapi_secret = "piapi-secret-for-log-test"
    elevenlabs_secret = "elevenlabs-secret-for-log-test"
    modelslab_secret = "modelslab-secret-for-log-test"

    monkeypatch.setattr(settings, "PIAPI_API_KEY_LITINKAI", piapi_secret)
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", elevenlabs_secret)
    monkeypatch.setattr(settings, "MODELSLAB_API_KEY", modelslab_secret)

    adapter = PiAPIAudioAdapter(
        piapi=SecretFailingPiAPIClient(piapi_secret),
        tts_router=SecretFailingTTSRouter(elevenlabs_secret),
        modelslab_service=SecretFailingModelsLabAudioService(modelslab_secret),
    )

    with caplog.at_level(logging.WARNING):
        result = await adapter.synthesize_text(
            text="A failed line of dialogue.",
            voice_id="voice-123",
            user_tier="standard",
        )

    assert result["status"] == "error"
    combined_logs = "\n".join(record.getMessage() for record in caplog.records)
    combined_output = f"{combined_logs}\n{result['error']}"

    assert piapi_secret not in combined_output
    assert elevenlabs_secret not in combined_output
    assert modelslab_secret not in combined_output
    assert "***" in combined_output
