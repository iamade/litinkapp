import logging

import pytest

from app.core.config import settings
from app.core.services.model_fallback import ModelFallbackManager
from app.core.services.provider_router import ProviderRouter, ProviderSkipError
from tests.test_script_ladder_429_cooldown import FakeRedis


@pytest.mark.asyncio
async def test_featherless_soft_skip_does_not_consume_attempt_or_set_cooldown(
    monkeypatch, caplog
):
    monkeypatch.setattr(settings, "FEATHERLESS_SUB_ACTIVE", False)
    router = ProviderRouter()
    with pytest.raises(ProviderSkipError):
        router.get_client_and_model("featherless/zai-org/GLM-5.2")

    async def no_sleep(_seconds):
        return None

    async def generate(model):
        if model.startswith("featherless/"):
            raise ProviderSkipError("featherless sub lapsed, awaiting renewal")
        return {"status": "success", "model_used": model}

    redis = FakeRedis()
    manager = ModelFallbackManager(redis_service=redis, sleep=no_sleep)
    with caplog.at_level(logging.INFO):
        result = await manager.try_model_list_with_fallback(
            ["featherless/zai-org/GLM-5.2", "zai/glm-5.2"],
            generate,
            {"model": "featherless/zai-org/GLM-5.2"},
            model_param_name="model",
        )
    assert result["status"] == "success"
    assert result["attempts"] == 1
    assert manager.cooldown_key("featherless") not in redis.values
    assert "[ScriptModelRouter] featherless skipped (sub lapsed)" in caplog.text

    monkeypatch.setattr(settings, "FEATHERLESS_SUB_ACTIVE", True)
    sentinel = object()
    router.featherless_client = sentinel
    client, resolved = router.get_client_and_model("featherless/zai-org/GLM-5.2")
    assert client is sentinel
    assert resolved == "zai-org/GLM-5.2"
