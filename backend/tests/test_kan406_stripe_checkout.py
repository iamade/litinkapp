import pytest

from app.api.services.subscription import SubscriptionManager, SubscriptionTier


class _FakeCheckoutSession:
    id = "cs_test_kan406"
    url = "https://checkout.stripe.test/session"


@pytest.mark.asyncio
async def test_checkout_session_uses_existing_customer(monkeypatch):
    captured_payload = {}

    def fake_create(**payload):
        captured_payload.update(payload)
        return _FakeCheckoutSession()

    monkeypatch.setattr(
        "app.api.services.subscription.settings.STRIPE_BASIC_PRICE_ID",
        "price_basic_active",
    )
    monkeypatch.setattr(
        "app.api.services.subscription.stripe.checkout.Session.create",
        fake_create,
    )

    manager = SubscriptionManager(session=None)
    result = await manager.create_checkout_session(
        user_id="user-123",
        tier=SubscriptionTier.BASIC,
        success_url="https://litinkai.test/success",
        cancel_url="https://litinkai.test/cancel",
        customer_id="cus_existing",
    )

    assert result == {
        "checkout_url": "https://checkout.stripe.test/session",
        "session_id": "cs_test_kan406",
    }
    assert captured_payload["customer"] == "cus_existing"
    assert captured_payload["line_items"][0]["price"] == "price_basic_active"
    assert captured_payload["metadata"] == {"user_id": "user-123", "tier": "basic"}


@pytest.mark.asyncio
async def test_enterprise_checkout_uses_custom_sales_flow(monkeypatch):
    def fail_if_called(**payload):
        raise AssertionError("Stripe checkout should not be called for enterprise")

    monkeypatch.setattr(
        "app.api.services.subscription.stripe.checkout.Session.create",
        fail_if_called,
    )

    manager = SubscriptionManager(session=None)

    with pytest.raises(ValueError, match="custom sales flow"):
        await manager.create_checkout_session(
            user_id="user-123",
            tier=SubscriptionTier.ENTERPRISE,
            success_url="https://litinkai.test/success",
            cancel_url="https://litinkai.test/cancel",
            customer_id="cus_existing",
        )
