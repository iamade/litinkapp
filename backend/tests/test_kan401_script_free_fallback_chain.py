from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.model_config import get_model_config
from app.core.services import model_fallback as model_fallback_module
from app.core.services.model_fallback import ModelFallbackManager
from app.core.services.provider_router import ProviderRouter


def _chain(config):
    return [
        model
        for model in (
            config.primary,
            config.fallback,
            config.fallback2,
            config.fallback3,
            config.fallback4,
            config.fallback5,
            config.fallback6,
        )
        if model
    ]


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


def test_script_free_chain_preserves_ollama_primary_and_adds_kan401_providers():
    config = get_model_config("script", "free")

    assert _chain(config) == [
        "ollama/gemma4:31b",
        "zai/glm-5.2",
        "piapi/gpt-4o-mini",
        "featherless/meta-llama/Meta-Llama-3.1-8B-Instruct",
        "ollama/ministral-3:8b",
        "ollama/gemma3:12b",
        "ollama/gemma3:4b",
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
        "featherless/meta-llama/Meta-Llama-3.1-8B-Instruct"
    ) == (
        router.featherless_client,
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
    )


@pytest.mark.parametrize(
    ("model", "expected_env"),
    [
        ("zai/glm-5.2", "Z_AI_API_KEY"),
        ("piapi/gpt-4o-mini", "PIAPI_API_KEY_LITINKAI"),
        (
            "featherless/meta-llama/Meta-Llama-3.1-8B-Instruct",
            "FEATHERLESS_API_KEY_LITINKAI",
        ),
    ],
)
def test_provider_router_reports_exact_missing_kan401_key(model, expected_env):
    router = ProviderRouter()
    router.zai_client = None
    router.piapi_client = None
    router.featherless_client = None

    with pytest.raises(ValueError) as exc_info:
        router.get_client_and_model(model)

    assert expected_env in str(exc_info.value)


@pytest.mark.asyncio
async def test_script_free_fallback_manager_attempts_full_kan401_chain(monkeypatch):
    calls = []

    async def no_sleep(_seconds):
        return None

    async def fake_generation(**kwargs):
        calls.append(kwargs["model_id"])
        if kwargs["model_id"].startswith("featherless/"):
            return {"status": "success"}
        return {"status": "error", "error": "429 rate limit"}

    monkeypatch.setattr(model_fallback_module.asyncio, "sleep", no_sleep)

    manager = ModelFallbackManager()
    result = await manager.try_with_fallback(
        service_type="script",
        user_tier="free",
        generation_function=fake_generation,
        request_params={},
    )

    assert result["status"] == "success"
    assert calls == [
        "ollama/gemma4:31b",
        "zai/glm-5.2",
        "piapi/gpt-4o-mini",
        "featherless/meta-llama/Meta-Llama-3.1-8B-Instruct",
    ]
    assert result["model_used"] == "featherless/meta-llama/Meta-Llama-3.1-8B-Instruct"
