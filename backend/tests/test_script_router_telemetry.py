import logging

import pytest

from app.core.model_config import ModelTier
from app.core.services import script_model_router
from app.core.services.script_model_router import ScriptModelRouter


@pytest.mark.asyncio
async def test_generate_script_emits_structured_resolution_telemetry(
    monkeypatch, caplog
):
    async def fake_fallback(**_kwargs):
        return {
            "status": "success",
            "content": "SCRIPT",
            "model_used": "zai/glm-5.2",
            "attempts": 1,
            "attempted_models": [{"model": "zai/glm-5.2", "status": "success"}],
        }

    monkeypatch.setattr(
        script_model_router.fallback_manager,
        "try_with_fallback",
        fake_fallback,
    )
    with caplog.at_level(logging.INFO):
        result = await ScriptModelRouter().generate_script(
            content="A short scene",
            user_tier=ModelTier.FREE,
            request_id="request-123",
            user_id="user-456",
        )

    assert result["telemetry"]["request_id"] == "request-123"
    assert result["telemetry"]["user_id"] == "user-456"
    assert result["telemetry"]["resolved_model"] == "zai/glm-5.2"
    # KAN-480: telemetry must retain the complete configured order.
    assert result["telemetry"]["ladder"] == [
        "ollama/gemma4:31b",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4-5-20251001",
        "minimax/MiniMax-M2",
        "zai/glm-5.2",
        "zai/glm-5.1",
    ]
    assert result["telemetry"]["success"] is True
    assert "[ScriptModelRouter] telemetry" in caplog.text
