import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")

from app.api.services.subscription import SubscriptionManager, SubscriptionTier
from app.core.config import settings
from app.core.model_config import get_model_config
from app.core.services.provider_router import ProviderRouter


@pytest.mark.asyncio
async def test_subscription_checkout_pro_uses_standard_price_with_pro_fallback(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_STANDARD_PRICE_ID", None)
    monkeypatch.setattr(settings, "STRIPE_PRO_PRICE_ID", "price_legacy_pro")

    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="cs_test_123", url="https://checkout.stripe.test/session")

    monkeypatch.setattr("stripe.checkout.Session.create", fake_create)

    manager = SubscriptionManager(session=None)
    result = await manager.create_checkout_session(
        user_id="user-123",
        tier=SubscriptionTier.PRO,
        success_url="https://litinkai.com/subscription?success=true",
        cancel_url="https://litinkai.com/subscription?cancelled=true",
    )

    assert captured["line_items"][0]["price"] == "price_legacy_pro"
    assert captured["mode"] == "subscription"
    assert result == {
        "checkout_url": "https://checkout.stripe.test/session",
        "session_id": "cs_test_123",
    }


@pytest.mark.asyncio
async def test_subscription_checkout_reports_missing_price_env(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_STANDARD_PRICE_ID", None)
    monkeypatch.setattr(settings, "STRIPE_PRO_PRICE_ID", None)

    manager = SubscriptionManager(session=None)

    with pytest.raises(ValueError) as exc_info:
        await manager.create_checkout_session(
            user_id="user-123",
            tier=SubscriptionTier.PRO,
            success_url="https://litinkai.com/subscription?success=true",
            cancel_url="https://litinkai.com/subscription?cancelled=true",
        )

    assert "STRIPE_STANDARD_PRICE_ID or STRIPE_PRO_PRICE_ID" in str(exc_info.value)


def test_free_basic_script_config_prefers_featherless_before_ollama():
    free_config = get_model_config("script", "free")
    basic_config = get_model_config("script", "basic")

    assert free_config.primary.startswith("featherless/")
    assert basic_config.primary.startswith("featherless/")
    assert free_config.fallback == "google/gemini-2.5-flash"
    assert basic_config.fallback == "google/gemini-2.5-flash"


@pytest.mark.asyncio
async def test_provider_router_limits_featherless_chat_completion(monkeypatch):
    monkeypatch.setattr(settings, "FEATHERLESS_API_KEY", "dummy")
    monkeypatch.setattr(settings, "FEATHERLESS_CONCURRENCY_LIMIT", 4)

    active_calls = 0
    max_active_calls = 0

    class _Completions:
        async def create(self, **kwargs):
            nonlocal active_calls, max_active_calls
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
            active_calls -= 1
            return kwargs["model"]

    router = ProviderRouter()
    router.featherless_client = SimpleNamespace(
        chat=SimpleNamespace(completions=_Completions())
    )

    result = await router.chat_completion(
        "featherless/meta-llama/Meta-Llama-3.1-8B-Instruct",
        [{"role": "user", "content": "hello"}],
    )

    assert result == "meta-llama/Meta-Llama-3.1-8B-Instruct"
    assert max_active_calls <= 4


def test_provider_router_skips_ollama_when_rate_limited(monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_RATE_LIMITED", True)

    router = ProviderRouter()

    with pytest.raises(ValueError) as exc_info:
        router.get_client_and_model("ollama/gemma4:31b")

    assert "OLLAMA_RATE_LIMITED" in str(exc_info.value)
