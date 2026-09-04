import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.subscriptions import routes as subscription_routes
from app.api.services import subscription as subscription_service
from app.auth.models import User
from app.main import app
from app.subscriptions.models import (
    SubscriptionStatus,
    SubscriptionTier,
    UserSubscription,
)


pytestmark = pytest.mark.asyncio

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
SUBSCRIPTION_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PERIOD_END = 1_899_999_999


class _Result:
    def __init__(self, first=None):
        self._first = first

    def first(self):
        return self._first


class _FakeSession:
    def __init__(self, *results):
        self.results = list(results)
        self.added = []
        self.commits = 0
        self.refreshes = []

    async def exec(self, statement):
        assert self.results, f"unexpected query: {statement}"
        return _Result(self.results.pop(0))

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        self.refreshes.append(item)


async def _override_session(fake_session):
    async def _inner():
        return fake_session

    return _inner


async def _override_user(user):
    async def _inner():
        return user

    return _inner


def _user():
    return User(
        id=USER_ID,
        email="kan462@example.com",
        hashed_password="x",
        is_active=True,
        first_name="Kan",
        last_name="Tester",
    )


def _subscription(**overrides):
    data = {
        "id": SUBSCRIPTION_ID,
        "user_id": USER_ID,
        "tier": SubscriptionTier.PRO,
        "status": SubscriptionStatus.ACTIVE,
        "stripe_customer_id": "cus_123",
        "stripe_subscription_id": "sub_123",
        "current_period_end": datetime.fromtimestamp(PERIOD_END, tz=timezone.utc),
    }
    data.update(overrides)
    return UserSubscription(**data)


async def _client_with_overrides(fake_session, user=None):
    app.dependency_overrides[subscription_routes.get_session] = await _override_session(
        fake_session
    )
    app.dependency_overrides[
        subscription_routes.get_current_active_user
    ] = await _override_user(user or _user())
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_cancel_endpoint_schedules_period_end_and_syncs_local_state(monkeypatch):
    subscription = _subscription()
    fake_session = _FakeSession(subscription)
    cancel_mock = AsyncMock(
        return_value={
            "subscription_id": "sub_123",
            "status": "active",
            "cancel_at_period_end": True,
            "current_period_end": PERIOD_END,
        }
    )
    monkeypatch.setattr(subscription_service.stripe_service, "cancel_subscription", cancel_mock)

    async with await _client_with_overrides(fake_session) as client:
        response = await client.post("/api/v1/subscriptions/cancel", json={})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "subscription_id": str(SUBSCRIPTION_ID),
        "status": "active",
        "cancel_at_period_end": True,
        "current_period_end": PERIOD_END,
    }
    cancel_mock.assert_awaited_once_with("sub_123", immediate=False)
    assert subscription.cancel_at_period_end is True
    assert subscription.current_period_end == datetime.fromtimestamp(
        PERIOD_END, tz=timezone.utc
    )
    assert fake_session.commits == 1


async def test_cancel_endpoint_is_idempotent_for_already_cancelled(monkeypatch):
    subscription = _subscription(
        tier=SubscriptionTier.FREE,
        status=SubscriptionStatus.CANCELLED,
        cancel_at_period_end=False,
    )
    fake_session = _FakeSession(subscription)
    cancel_mock = AsyncMock()
    monkeypatch.setattr(subscription_service.stripe_service, "cancel_subscription", cancel_mock)

    async with await _client_with_overrides(fake_session) as client:
        response = await client.post("/api/v1/subscriptions/cancel", json={"immediate": True})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancel_at_period_end"] is False
    cancel_mock.assert_not_awaited()
    assert fake_session.commits == 0


async def test_status_endpoint_prefers_stripe_and_persists_real_state(monkeypatch):
    subscription = _subscription(cancel_at_period_end=False)
    fake_session = _FakeSession(subscription)
    get_mock = AsyncMock(
        return_value={
            "id": "sub_123",
            "status": "active",
            "current_period_end": PERIOD_END,
            "cancel_at_period_end": True,
            "price_id": "price_pro",
        }
    )
    monkeypatch.setattr(subscription_service.stripe_service, "get_subscription", get_mock)

    async with await _client_with_overrides(fake_session) as client:
        response = await client.get("/api/v1/subscriptions/status")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "pro"
    assert body["tier"] == "pro"
    assert body["status"] == "active"
    assert body["cancel_at_period_end"] is True
    assert body["source"] == "stripe"
    assert body["stripe_subscription_id"] == "sub_123"
    get_mock.assert_awaited_once_with("sub_123")
    assert subscription.stripe_price_id == "price_pro"
    assert fake_session.commits == 1


async def test_status_endpoint_sticky_cancel_does_not_downgrade_local_fallback(
    monkeypatch,
):
    """KAN-462: local fallback cancel (cap=true) must survive a read-path
    re-sync where Stripe still reports the subscription active (cap=false).
    The sync must NOT downgrade cancel_at_period_end back to False."""
    subscription = _subscription(cancel_at_period_end=True)
    fake_session = _FakeSession(subscription)
    get_mock = AsyncMock(
        return_value={
            "id": "sub_123",
            "status": "active",
            "current_period_end": PERIOD_END,
            "cancel_at_period_end": False,  # Stripe says active, no cancel scheduled
            "price_id": "price_pro",
        }
    )
    monkeypatch.setattr(subscription_service.stripe_service, "get_subscription", get_mock)

    async with await _client_with_overrides(fake_session) as client:
        response = await client.get("/api/v1/subscriptions/status")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    # Local fallback cancel must be sticky — NOT downgraded to False
    assert body["cancel_at_period_end"] is True
    assert subscription.cancel_at_period_end is True
    assert body["source"] == "stripe"


async def test_webhook_subscription_deleted_syncs_local_subscription():
    subscription = _subscription(status=SubscriptionStatus.ACTIVE, tier=SubscriptionTier.PRO)
    fake_session = _FakeSession(subscription)
    manager = subscription_service.SubscriptionManager(fake_session)

    await manager.handle_subscription_webhook(
        "subscription.deleted",
        {
            "event_type": "subscription.deleted",
            "subscription_id": "sub_123",
            "status": "canceled",
            "current_period_end": PERIOD_END,
            "cancel_at_period_end": True,
        },
    )

    assert subscription.status == SubscriptionStatus.CANCELLED
    assert subscription.tier == SubscriptionTier.FREE
    assert subscription.cancel_at_period_end is False
    assert subscription.cancelled_at is not None
    assert fake_session.commits == 1
    history = fake_session.added[-1]
    assert history.event_type == "subscription.deleted"
    assert history.from_status == SubscriptionStatus.ACTIVE
    assert history.to_status == SubscriptionStatus.CANCELLED


async def test_cancel_endpoint_falls_back_to_local_when_stripe_missing(monkeypatch):
    subscription = _subscription()
    fake_session = _FakeSession(subscription)
    cancel_mock = AsyncMock(
        side_effect=Exception(
            "Request req_test: No such subscription: 'sub_test_kan462_pro'"
        )
    )
    monkeypatch.setattr(subscription_service.stripe_service, "cancel_subscription", cancel_mock)

    async with await _client_with_overrides(fake_session) as client:
        response = await client.post("/api/v1/subscriptions/cancel", json={})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "subscription_id": str(SUBSCRIPTION_ID),
        "status": "active",
        "cancel_at_period_end": True,
        "current_period_end": PERIOD_END,
    }
    assert subscription.cancel_at_period_end is True
    assert fake_session.commits == 1


async def test_cancel_endpoint_stripe_missing_immediate_cancels_locally(monkeypatch):
    monkeypatch.setattr(subscription_routes.settings, "ALLOW_IMMEDIATE_CANCEL", True)
    subscription = _subscription()
    fake_session = _FakeSession(subscription)
    cancel_mock = AsyncMock(
        side_effect=Exception(
            "Request req_test: No such subscription: 'sub_test_kan462_pro'"
        )
    )
    monkeypatch.setattr(subscription_service.stripe_service, "cancel_subscription", cancel_mock)

    async with await _client_with_overrides(fake_session) as client:
        response = await client.post(
            "/api/v1/subscriptions/cancel", json={"immediate": True}
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancel_at_period_end"] is False
    assert subscription.status == SubscriptionStatus.CANCELLED
    assert subscription.tier == SubscriptionTier.FREE
    assert fake_session.commits == 1


async def test_checkout_service_maps_invalid_price_to_value_error(monkeypatch):
    """KAN-462: Stripe rejecting a misconfigured price ID must surface as a
    clear ValueError (route -> 400), never an opaque 500."""
    import stripe as stripe_module

    def raise_invalid_request(*args, **kwargs):
        raise stripe_module.error.InvalidRequestError(
            message="No such price: 'price_1TeQI66U8P1S4aG1xkSBdEiG'",
            param="line_items[0][price]",
        )

    monkeypatch.setattr(
        subscription_service.stripe.checkout.Session, "create", raise_invalid_request
    )
    manager = subscription_service.SubscriptionManager(_FakeSession())
    with pytest.raises(ValueError) as exc_info:
        await manager.create_checkout_session(
            user_id=str(USER_ID),
            tier=SubscriptionTier.BASIC,
            success_url="https://test.litinkai.com/success",
            cancel_url="https://test.litinkai.com/cancel",
            billing_period="monthly",
        )
    assert "not correctly configured" in str(exc_info.value)


async def test_checkout_endpoint_returns_400_on_invalid_price(monkeypatch):
    """KAN-462: /subscriptions/checkout returns 400 with a clear message when
    the configured Stripe price ID does not exist."""
    import stripe as stripe_module

    def raise_invalid_request(*args, **kwargs):
        raise stripe_module.error.InvalidRequestError(
            message="No such price: 'price_1TeQI66U8P1S4aG1xkSBdEiG'",
            param="line_items[0][price]",
        )

    monkeypatch.setattr(
        subscription_service.stripe.checkout.Session, "create", raise_invalid_request
    )

    user = SimpleNamespace(
        id=USER_ID,
        email="psq.kan462.pro@test.litinkai.com",
        full_name="PSQ Kan462 Pro",
    )

    async def fake_get_user(*args, **kwargs):
        return _Result(user)

    async def override_session():
        yield _FakeSession()

    app.dependency_overrides[subscription_routes.get_session] = override_session
    app.dependency_overrides[subscription_routes.get_current_active_user] = (
        lambda: user
    )

    customer_mock = AsyncMock(return_value="cus_test_kan462_pro")
    monkeypatch.setattr(
        subscription_service.stripe_service, "create_or_get_customer", customer_mock
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/subscriptions/checkout",
            json={
                "tier": "basic",
                "success_url": "https://test.litinkai.com/success",
                "cancel_url": "https://test.litinkai.com/cancel",
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "not correctly configured" in response.json()["detail"]
