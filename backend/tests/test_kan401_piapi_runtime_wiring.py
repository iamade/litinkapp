from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.services.provider_router import ProviderRouter


def test_settings_reads_corrected_litinkai_piapi_env_name(monkeypatch):
    monkeypatch.setenv("PIAPI_API_KEY_LITINKAI", "piapi-secret")
    monkeypatch.delenv("PIPAP_API_KEY_LITINKAI", raising=False)
    monkeypatch.delenv("PIAPI_API_KEY", raising=False)

    settings = Settings()

    assert settings.piapi_api_key == "piapi-secret"


def test_settings_supports_legacy_pipap_typo_env_name(monkeypatch):
    monkeypatch.delenv("PIAPI_API_KEY_LITINKAI", raising=False)
    monkeypatch.setenv("PIPAP_API_KEY_LITINKAI", "legacy-secret")
    monkeypatch.delenv("PIAPI_API_KEY", raising=False)

    settings = Settings()

    assert settings.piapi_api_key == "legacy-secret"


def test_provider_router_routes_piapi_prefixed_models(monkeypatch):
    router = ProviderRouter()
    router.piapi_client = SimpleNamespace()

    client, resolved_model = router.get_client_and_model("piapi/test-model")

    assert client is router.piapi_client
    assert resolved_model == "test-model"


def test_provider_router_rejects_piapi_prefix_without_runtime_key():
    router = ProviderRouter()
    router.piapi_client = None

    with pytest.raises(ValueError) as exc_info:
        router.get_client_and_model("piapi/test-model")

    assert "PIAPI_API_KEY_LITINKAI" in str(exc_info.value)
