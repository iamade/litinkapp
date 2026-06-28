"""KAN-406: Backend monthly/annual Stripe price-id selection from billing_period.

Verifies:
  1. billing_period=monthly → uses _PRICE_ID (no suffix)
  2. billing_period=annual  → uses _PRICE_ID_ANNUAL env vars
  3. Defaults to monthly when billing_period is absent
  4. Error messages include billing_period in wording
"""
import os
import pytest
from types import SimpleNamespace

os.environ.setdefault("STRIPE_SECRET_KEY", "***")
os.environ.setdefault("FEATHERLESS_API_KEY", "***")

import asyncio

from app.api.services.subscription import SubscriptionManager, SubscriptionTier
from app.core.config import settings


def _sync(coro):
    """Run async coroutine synchronously for test assertion."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def manager():
    return SubscriptionManager(session=None)


class TestKAN406BillingPeriodPriceIds:

    def test_monthly_uses_monthly_price_ids(self, manager, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_STANDARD_PRICE_ID", "price_monthly_std")
        monkeypatch.setattr(settings, "STRIPE_BASIC_PRICE_ID", "price_monthly_basic")

        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(id="cs_test_m", url="https://checkout.stripe.test/m")

        monkeypatch.setattr("stripe.checkout.Session.create", fake_create)

        _sync(manager.create_checkout_session(
            user_id="user-123",
            tier=SubscriptionTier.PRO,
            success_url="https://litinkai.com/sub",
            cancel_url="https://litinkai.com/cancel",
            billing_period="monthly",
        ))

        assert captured["line_items"][0]["price"] == "price_monthly_std"
        assert captured["mode"] == "subscription"

    def test_annual_uses_annual_price_ids(self, manager, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_STANDARD_PRICE_ID_ANNUAL", "price_annual_std")
        monkeypatch.setattr(settings, "STRIPE_BASIC_PRICE_ID_ANNUAL", "price_annual_basic")

        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(id="cs_test_a", url="https://checkout.stripe.test/a")

        monkeypatch.setattr("stripe.checkout.Session.create", fake_create)

        _sync(manager.create_checkout_session(
            user_id="user-123",
            tier=SubscriptionTier.BASIC,
            success_url="https://litinkai.com/sub",
            cancel_url="https://litinkai.com/cancel",
            billing_period="annual",
        ))

        assert captured["line_items"][0]["price"] == "price_annual_basic"

    def test_annual_missing_env_raises_with_period_in_message(self, manager, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_STANDARD_PRICE_ID_ANNUAL", None)
        monkeypatch.setattr(settings, "STRIPE_STANDARD_PRICE_ID", None)
        monkeypatch.setattr(settings, "STRIPE_PRO_PRICE_ID", None)

        with pytest.raises(ValueError) as exc_info:
            _sync(manager.create_checkout_session(
                user_id="user-123",
                tier=SubscriptionTier.PRO,
                success_url="https://litinkai.com/sub",
                cancel_url="https://litinkai.com/cancel",
                billing_period="annual",
            ))

        msg = str(exc_info.value)
        assert "annual" in msg.lower()
        assert "_ANNUAL" in msg

    def test_monthly_missing_env_does_not_mention_annual(self, manager, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_STANDARD_PRICE_ID", None)
        monkeypatch.setattr(settings, "STRIPE_PRO_PRICE_ID", None)

        with pytest.raises(ValueError) as exc_info:
            _sync(manager.create_checkout_session(
                user_id="user-123",
                tier=SubscriptionTier.PRO,
                success_url="https://litinkai.com/sub",
                cancel_url="https://litinkai.com/cancel",
                billing_period="monthly",
            ))

        msg = str(exc_info.value)
        assert "_ANNUAL" not in msg
        assert "monthly" in msg.lower()

    def test_defaults_to_monthly_when_billing_period_absent(self, manager, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_STANDARD_PRICE_ID", "price_monthly_default")

        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(id="cs_default", url="https://checkout.stripe.test/d")

        monkeypatch.setattr("stripe.checkout.Session.create", fake_create)

        _sync(manager.create_checkout_session(
            user_id="u1",
            tier=SubscriptionTier.PRO,
            success_url="https://litinkai.com/s",
            cancel_url="https://litinkai.com/c",
        ))

        assert captured["line_items"][0]["price"] == "price_monthly_default"