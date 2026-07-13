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
    assert result["telemetry"]["ladder"][0] == "zai/glm-5.2"
    assert len(result["telemetry"]["ladder"]) == 8
    assert result["telemetry"]["success"] is True
    assert "[ScriptModelRouter] telemetry" in caplog.text
