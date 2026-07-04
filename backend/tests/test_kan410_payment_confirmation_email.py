import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.services.subscription import SubscriptionManager
from app.auth.models import User
from app.subscriptions.models import SubscriptionTier


class _Result:
    def __init__(self, value):
        self.value = value

    def first(self):
        return self.value


@pytest.mark.asyncio
async def test_checkout_completed_sends_payment_confirmation_email(monkeypatch):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="author@example.com",
        hashed_password="hashed",
        first_name="Ada",
        last_name="Writer",
        is_active=True,
    )

    session = MagicMock()
    session.exec = AsyncMock(side_effect=[_Result(None), _Result(user)])
    session.commit = AsyncMock()

    send_email = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.api.services.subscription.email_service.send_email", send_email
    )
    monkeypatch.setattr(
        "app.api.services.subscription.settings.FRONTEND_URL",
        "https://app.litinkai.com",
    )

    manager = SubscriptionManager(session=session)

    await manager.handle_subscription_webhook(
        "checkout.session.completed",
        {
            "object": {
                "metadata": {
                    "user_id": str(user_id),
                    "tier": SubscriptionTier.BASIC.value,
                },
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
            }
        },
    )

    send_email.assert_awaited_once()
    to_email, subject, html_content, text_content = send_email.await_args.args

    assert to_email == "author@example.com"
    assert subject == "Payment Confirmed - Your LitInkAI Subscription is Active"
    assert "Basic subscription is now active" in html_content
    assert "https://app.litinkai.com/dashboard" in html_content
    assert "https://app.litinkai.com/dashboard" in text_content
