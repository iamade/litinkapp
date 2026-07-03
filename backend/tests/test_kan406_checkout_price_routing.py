from app.api.services.subscription import SubscriptionManager
from app.core.config import settings
from app.subscriptions.models import SubscriptionTier


def _clear_stripe_price_settings(monkeypatch):
    for name in (
        "STRIPE_BASIC_PRICE_ID",
        "STRIPE_STANDARD_PRICE_ID",
        "STRIPE_PRO_PRICE_ID",
        "STRIPE_PREMIUM_PRICE_ID",
        "STRIPE_PROFESSIONAL_PRICE_ID",
        "STRIPE_BASIC_MONTHLY_PRICE_ID",
        "STRIPE_BASIC_ANNUAL_PRICE_ID",
        "STRIPE_STANDARD_MONTHLY_PRICE_ID",
        "STRIPE_STANDARD_ANNUAL_PRICE_ID",
        "STRIPE_PREMIUM_MONTHLY_PRICE_ID",
        "STRIPE_PREMIUM_ANNUAL_PRICE_ID",
        "STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID",
        "STRIPE_PROFESSIONAL_ANNUAL_PRICE_ID",
    ):
        monkeypatch.setattr(settings, name, None)


def test_kan406_resolves_basic_monthly_and_annual_prices(monkeypatch):
    _clear_stripe_price_settings(monkeypatch)
    monkeypatch.setattr(settings, "STRIPE_BASIC_MONTHLY_PRICE_ID", "price_basic_month")
    monkeypatch.setattr(settings, "STRIPE_BASIC_ANNUAL_PRICE_ID", "price_basic_year")

    manager = SubscriptionManager(session=None)

    assert (
        manager._get_price_id_for_tier(SubscriptionTier.BASIC, "monthly")
        == "price_basic_month"
    )
    assert (
        manager._get_price_id_for_tier(SubscriptionTier.BASIC, "annual")
        == "price_basic_year"
    )


def test_kan406_internal_pro_uses_standard_per_period_prices(monkeypatch):
    _clear_stripe_price_settings(monkeypatch)
    monkeypatch.setattr(
        settings, "STRIPE_STANDARD_MONTHLY_PRICE_ID", "price_standard_month"
    )
    monkeypatch.setattr(
        settings, "STRIPE_STANDARD_ANNUAL_PRICE_ID", "price_standard_year"
    )

    manager = SubscriptionManager(session=None)

    assert (
        manager._get_price_id_for_tier(SubscriptionTier.PRO, "monthly")
        == "price_standard_month"
    )
    assert (
        manager._get_price_id_for_tier(SubscriptionTier.PRO, "annual")
        == "price_standard_year"
    )


def test_kan406_keeps_legacy_single_price_fallback(monkeypatch):
    _clear_stripe_price_settings(monkeypatch)
    monkeypatch.setattr(settings, "STRIPE_PREMIUM_PRICE_ID", "price_premium_legacy")

    manager = SubscriptionManager(session=None)

    assert (
        manager._get_price_id_for_tier(SubscriptionTier.PREMIUM, "monthly")
        == "price_premium_legacy"
    )
