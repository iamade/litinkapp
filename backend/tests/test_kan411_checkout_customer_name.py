from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.services.subscription import SubscriptionManager
from app.core.config import settings
from app.subscriptions.models import SubscriptionTier


@pytest.mark.asyncio
async def test_checkout_session_uses_existing_customer_and_name_metadata(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_BASIC_MONTHLY_PRICE_ID", "price_basic_month")
    session_create = MagicMock(
        return_value=SimpleNamespace(url="https://checkout.stripe.test", id="cs_test")
    )
    monkeypatch.setattr(
        "app.api.services.subscription.stripe.checkout.Session.create",
        session_create,
    )

    manager = SubscriptionManager(session=None)

    response = await manager.create_checkout_session(
        user_id="user-123",
        tier=SubscriptionTier.BASIC,
        success_url="https://app.litinkai.com/success",
        cancel_url="https://app.litinkai.com/cancel",
        billing_period="monthly",
        customer_id="cus_test_123",
        customer_email="author@example.com",
        customer_name="Ada Writer",
    )

    assert response == {
        "checkout_url": "https://checkout.stripe.test",
        "session_id": "cs_test",
    }

    session_create.assert_called_once()
    kwargs = session_create.call_args.kwargs
    assert kwargs["customer"] == "cus_test_123"
    assert "customer_email" not in kwargs
    assert kwargs["metadata"]["customer_name"] == "Ada Writer"
    assert kwargs["metadata"]["user_id"] == "user-123"
    assert kwargs["metadata"]["tier"] == "basic"


@pytest.mark.asyncio
async def test_checkout_session_uses_customer_email_when_customer_id_missing(
    monkeypatch,
):
    monkeypatch.setattr(settings, "STRIPE_BASIC_MONTHLY_PRICE_ID", "price_basic_month")
    session_create = MagicMock(
        return_value=SimpleNamespace(url="https://checkout.stripe.test", id="cs_test")
    )
    monkeypatch.setattr(
        "app.api.services.subscription.stripe.checkout.Session.create",
        session_create,
    )

    manager = SubscriptionManager(session=None)

    await manager.create_checkout_session(
        user_id="user-123",
        tier=SubscriptionTier.BASIC,
        success_url="https://app.litinkai.com/success",
        cancel_url="https://app.litinkai.com/cancel",
        billing_period="monthly",
        customer_email="author@example.com",
    )

    kwargs = session_create.call_args.kwargs
    assert kwargs["customer_email"] == "author@example.com"
    assert "customer" not in kwargs
