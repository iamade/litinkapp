from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.model_config import get_model_config
from app.core.services.model_fallback import ModelFallbackManager
from app.core.services.provider_router import (
    ProviderNotConfiguredError,
    ProviderRouter,
)


def _chain(config):
    return config.models


class _FakeRedis:
    def __init__(self):
        self.is_connected = True
        self.values = {}

    async def connect(self):
        self.is_connected = True

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, expire=None):
        self.values[key] = value

    async def delete(self, key):
        self.values.pop(key, None)


def test_settings_reads_kan401_canonical_provider_keys(monkeypatch):
    monkeypatch.setenv("Z_AI_API_KEY", "zai-secret")
    monkeypatch.setenv("PIAPI_API_KEY_LITINKAI", "piapi-secret")
    monkeypatch.setenv("FEATHERLESS_API_KEY_LITINKAI", "featherless-secret")
    monkeypatch.delenv("ZAI_API_KEY", raising=False)

    settings = Settings()

    assert settings.z_ai_api_key == "zai-secret"
    assert settings.piapi_api_key == "piapi-secret"
    assert settings.featherless_api_key == "featherless-secret"


def test_settings_keeps_existing_zai_env_spelling_as_legacy_fallback(monkeypatch):
    monkeypatch.delenv("Z_AI_API_KEY", raising=False)
    monkeypatch.setenv("ZAI_API_KEY", "legacy-zai-secret")

    settings = Settings()

    assert settings.z_ai_api_key == "legacy-zai-secret"


def test_script_free_chain_exposes_current_kan401_provider_ladder():
    config = get_model_config("script", "free")

    assert _chain(config) == [
        "zai/glm-5.2",
        "ollama/gemma4:31b",
        "featherless/zai-org/GLM-5.2",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4-5-20251001",
        "zai/glm-5.1",
        "minimax/MiniMax-M2",
    ]


def test_provider_router_routes_kan401_prefixed_models():
    router = ProviderRouter()
    router.zai_client = SimpleNamespace(name="zai")
    router.piapi_client = SimpleNamespace(name="piapi")
    router.featherless_client = SimpleNamespace(name="featherless")

    assert router.get_client_and_model("zai/glm-5.2") == (
        router.zai_client,
        "glm-5.2",
    )
    assert router.get_client_and_model("piapi/gpt-4o-mini") == (
        router.piapi_client,
        "gpt-4o-mini",
    )
    assert router.get_client_and_model(
        "featherless/zai-org/GLM-5.2", featherless_active=True
    ) == (
        router.featherless_client,
        "zai-org/GLM-5.2",
    )


@pytest.mark.parametrize(
    ("model", "expected_env"),
    [
        ("zai/glm-5.2", "Z_AI_API_KEY"),
        ("piapi/gpt-4o-mini", "PIAPI_API_KEY_LITINKAI"),
        (
            "featherless/zai-org/GLM-5.2",
            "FEATHERLESS_API_KEY_LITINKAI",
        ),
    ],
)
def test_provider_router_reports_exact_missing_kan401_key(model, expected_env):
    router = ProviderRouter()
    router.zai_client = None
    router.piapi_client = None
    router.featherless_client = None

    kwargs = {"featherless_active": True} if model.startswith("featherless/") else {}
    with pytest.raises(ProviderNotConfiguredError) as exc_info:
        router.get_client_and_model(model, **kwargs)

    assert expected_env in str(exc_info.value)


@pytest.mark.asyncio
async def test_script_free_fallback_manager_attempts_full_kan401_chain_without_redis():
    calls = []

    async def no_sleep(_seconds):
        return None

    async def fake_generation(**kwargs):
        calls.append(kwargs["model_id"])
        if kwargs["model_id"] == "piapi/gpt-4o-mini":
            return {"status": "success"}
        return {"status": "error", "error": "429 rate limit"}

    manager = ModelFallbackManager(redis_service=_FakeRedis(), sleep=no_sleep)
    result = await manager.try_with_fallback(
        service_type="script",
        user_tier="free",
        generation_function=fake_generation,
        request_params={},
    )

    assert result["status"] == "success"
    assert calls == [
        "zai/glm-5.2",
        "ollama/gemma4:31b",
        "featherless/zai-org/GLM-5.2",
        "piapi/gpt-4o-mini",
    ]
    assert result["model_used"] == "piapi/gpt-4o-mini"
    assert result["attempts"] == 4
