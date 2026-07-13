import pytest

from app.core.services import model_fallback
from app.core.services.model_fallback import ModelFallbackManager


class FakeRedis:
    def __init__(self):
        self.is_connected = True
        self.values = {}

    async def connect(self):
        self.is_connected = True

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, expire=3600):
        self.values[key] = value
        return True

    async def delete(self, key):
        self.values.pop(key, None)
        return True


@pytest.mark.asyncio
async def test_429_sets_provider_cooldown_and_skips_remaining_slots(monkeypatch):
    now = 1_000_000.0
    monkeypatch.setattr(model_fallback.time, "time", lambda: now)
    redis = FakeRedis()
    calls = []

    async def no_sleep(_seconds):
        return None

    async def generate(model):
        calls.append(model)
        if model.startswith("ollama/"):
            error = RuntimeError("429 Too Many Requests")
            error.status_code = 429
            raise error
        return {"status": "success", "model_used": model}

    manager = ModelFallbackManager(redis_service=redis, sleep=no_sleep)
    models = ["ollama/first", "ollama/second", "zai/fallback"]
    first = await manager.try_model_list_with_fallback(
        models, generate, {"model": models[0]}, model_param_name="model"
    )
    assert first["status"] == "success"
    assert calls == ["ollama/first", "zai/fallback"]
    assert manager.cooldown_key("ollama") in redis.values

    calls.clear()
    second = await manager.try_model_list_with_fallback(
        ["ollama/first", "zai/fallback"],
        generate,
        {"model": "ollama/first"},
        model_param_name="model",
    )
    assert second["status"] == "success"
    assert calls == ["zai/fallback"]

    now += model_fallback.PROVIDER_COOLDOWN_SECONDS + 1
    calls.clear()
    third = await manager.try_model_list_with_fallback(
        ["ollama/first", "zai/fallback"],
        generate,
        {"model": "ollama/first"},
        model_param_name="model",
    )
    assert calls[0] == "ollama/first"
    assert third["attempts"] == 2


@pytest.mark.asyncio
async def test_unprefixed_models_do_not_share_an_unknown_provider_cooldown():
    redis = FakeRedis()
    calls = []

    async def no_sleep(_seconds):
        return None

    async def generate(model):
        calls.append(model)
        if model == "first-unprefixed-model":
            error = RuntimeError("429 Too Many Requests")
            error.status_code = 429
            raise error
        return {"status": "success", "model_used": model}

    manager = ModelFallbackManager(redis_service=redis, sleep=no_sleep)
    result = await manager.try_model_list_with_fallback(
        ["first-unprefixed-model", "second-unprefixed-model"],
        generate,
        {"model": "first-unprefixed-model"},
        model_param_name="model",
    )

    assert result["status"] == "success"
    assert calls == ["first-unprefixed-model", "second-unprefixed-model"]
    assert manager.cooldown_key("unknown") not in redis.values


@pytest.mark.asyncio
async def test_timeout_stops_before_a_second_provider_attempt():
    redis = FakeRedis()
    calls = []

    async def no_sleep(_seconds):
        return None

    async def generate(model):
        calls.append(model)
        raise RuntimeError("request timed out while provider may still be processing")

    manager = ModelFallbackManager(redis_service=redis, sleep=no_sleep)
    result = await manager.try_model_list_with_fallback(
        ["ollama/first", "zai/second"],
        generate,
        {"model": "ollama/first"},
        model_param_name="model",
    )

    assert result["status"] == "error"
    assert calls == ["ollama/first"]
