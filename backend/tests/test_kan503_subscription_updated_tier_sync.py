"""Offline webhook regressions: subscription.updated must not leave a stale tier.

Sessions/grants are in-memory doubles; no Stripe request or database connection.
"""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.api.services import subscription as subscription_module
from app.api.services.subscription import SubscriptionManager
from app.credits.constants import TIER_CREDIT_GRANTS_BY_ENUM
from app.promo.models import CreditGrant, GrantType
from app.subscriptions.models import SubscriptionTier, SubscriptionStatus, UserSubscription


class Result:
    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class Session:
    def __init__(self, subscription, grants):
        self.subscription = subscription
        self.grants = grants
        self.added = []
        self.commits = 0

    async def exec(self, statement):
        sql = str(statement)
        if "user_subscriptions" in sql:
            return Result([self.subscription])
        if "credit_grants" in sql:
            return Result(self.grants)
        raise AssertionError(f"Unexpected query: {sql}")

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1


@pytest.fixture
def configured_prices(monkeypatch):
    values = {"STRIPE_SECRET_KEY": "sk_test_dummy"}
    for tier in SubscriptionTier:
        for suffix in ("PRICE_ID", "MONTHLY_PRICE_ID", "ANNUAL_PRICE_ID"):
            name = f"STRIPE_{tier.value.upper()}_{suffix}"
            if hasattr(subscription_module.settings, name):
                values[name] = f"price_{tier.value}_{suffix.lower()}"
    monkeypatch.setattr(subscription_module, "settings", SimpleNamespace(**values))
    return values


def setup_subscription(tier=SubscriptionTier.BASIC, remaining=1400, with_grant=True):
    now = datetime.now(timezone.utc)
    subscription = UserSubscription(
        user_id=uuid.uuid4(), tier=tier, status=SubscriptionStatus.ACTIVE,
        stripe_subscription_id="sub_unit", stripe_price_id="price_old",
        current_period_start=now - timedelta(days=10),
        current_period_end=now + timedelta(days=20),
    )
    grant = CreditGrant(
        user_id=subscription.user_id, credits_remaining=remaining, credits_used=100,
        expires_at=now + timedelta(days=365), grant_type=GrantType.PURCHASE.value,
    )
    session = Session(subscription, [grant] if with_grant else [])
    return subscription, grant, session


def event(price=None, normalized=False):
    payload = {"id": "sub_unit", "status": "active", "cancel_at_period_end": False}
    if price is not None:
        if normalized:
            payload["price_id"] = price
        else:
            payload["items"] = {"data": [{"price": {"id": price}}]}
    return {"object": payload}


@pytest.mark.asyncio
@pytest.mark.parametrize("target,suffix", [
    (tier, suffix)
    for tier in (SubscriptionTier.STANDARD, SubscriptionTier.PREMIUM, SubscriptionTier.PROFESSIONAL)
    for suffix in ("PRICE_ID", "MONTHLY_PRICE_ID", "ANNUAL_PRICE_ID")
] + [(SubscriptionTier.PRO, "PRICE_ID")])
async def test_customer_subscription_updated_resolves_price_and_adjusts_existing_grant(
    configured_prices, target, suffix
):
    sub, grant, session = setup_subscription()
    original_expiry = grant.expires_at
    price = configured_prices[f"STRIPE_{target.value.upper()}_{suffix}"]
    await SubscriptionManager(session).handle_subscription_webhook(
        "customer.subscription.updated", event(price)
    )
    assert sub.tier == target
    assert sub.stripe_price_id == price
    assert grant.credits_remaining == TIER_CREDIT_GRANTS_BY_ENUM[target.value] - 100
    assert grant.credits_used == 100
    assert grant.expires_at == original_expiry
    assert [x for x in session.added if isinstance(x, CreditGrant)] == [grant]
    assert session.commits == 1


@pytest.mark.asyncio
async def test_updated_downgrade_clamps_spent_balance_and_replay_never_stacks(configured_prices):
    sub, grant, session = setup_subscription(SubscriptionTier.PREMIUM, remaining=100)
    price = configured_prices["STRIPE_BASIC_MONTHLY_PRICE_ID"]
    manager = SubscriptionManager(session)
    for _ in range(2):
        await manager.handle_subscription_webhook("customer.subscription.updated", event(price))
    assert sub.tier == SubscriptionTier.BASIC
    assert grant.credits_remaining == 0
    assert [x for x in session.added if isinstance(x, CreditGrant)] == [grant]
    assert session.commits == 2


@pytest.mark.asyncio
async def test_updated_upgrade_replay_adjusts_only_once(configured_prices):
    sub, grant, session = setup_subscription()
    price = configured_prices["STRIPE_PREMIUM_ANNUAL_PRICE_ID"]
    manager = SubscriptionManager(session)
    for _ in range(2):
        await manager.handle_subscription_webhook("customer.subscription.updated", event(price))
    assert sub.tier == SubscriptionTier.PREMIUM
    assert grant.credits_remaining == 13000
    assert [x for x in session.added if isinstance(x, CreditGrant)] == [grant]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [event(), event("price_unconfigured"),
    {"object": {"id": "sub_unit", "status": "active", "items": {"data": []}}},
    {"object": {"id": "sub_unit", "status": "active", "items": {"data": [
        {"price": {"id": "price_premium_monthly_price_id"}},
        {"price": {"id": "price_basic_monthly_price_id"}}]}}}])
async def test_unknown_missing_or_multi_item_price_keeps_tier_and_grant(configured_prices, payload):
    sub, grant, session = setup_subscription()
    await SubscriptionManager(session).handle_subscription_webhook("customer.subscription.updated", payload)
    assert sub.tier == SubscriptionTier.BASIC
    assert grant.credits_remaining == 1400
    assert not any(isinstance(x, CreditGrant) for x in session.added)


@pytest.mark.asyncio
async def test_normalized_updated_event_uses_same_price_mapping(configured_prices):
    sub, grant, session = setup_subscription()
    price = configured_prices["STRIPE_PREMIUM_PRICE_ID"]
    await SubscriptionManager(session).handle_subscription_webhook("subscription.updated", event(price, normalized=True))
    assert sub.tier == SubscriptionTier.PREMIUM
    assert grant.credits_remaining == 13000


@pytest.mark.asyncio
async def test_price_update_without_live_grant_does_not_backfill_or_create_one(configured_prices):
    sub, _, session = setup_subscription(with_grant=False)
    price = configured_prices["STRIPE_PREMIUM_PRICE_ID"]
    await SubscriptionManager(session).handle_subscription_webhook("customer.subscription.updated", event(price))
    assert sub.tier == SubscriptionTier.PREMIUM
    assert not any(isinstance(x, CreditGrant) for x in session.added)


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["PRICE_ID", "MONTHLY_PRICE_ID", "ANNUAL_PRICE_ID"])
async def test_standard_price_preserves_legacy_pro_row_and_grant_values(configured_prices, suffix):
    sub, grant, session = setup_subscription(SubscriptionTier.PRO, remaining=4700)
    price = configured_prices[f"STRIPE_STANDARD_{suffix}"]
    await SubscriptionManager(session).handle_subscription_webhook("customer.subscription.updated", event(price))
    assert sub.tier == SubscriptionTier.PRO
    assert grant.credits_remaining == 4700
    assert TIER_CREDIT_GRANTS_BY_ENUM["pro"] == TIER_CREDIT_GRANTS_BY_ENUM["standard"] == 4800
    assert not any(isinstance(x, CreditGrant) for x in session.added)


@pytest.mark.asyncio
async def test_conflicting_configured_price_does_not_guess_tier(configured_prices):
    sub, grant, session = setup_subscription()
    subscription_module.settings.STRIPE_STANDARD_PRICE_ID = "price_shared"
    subscription_module.settings.STRIPE_PREMIUM_PRICE_ID = "price_shared"
    await SubscriptionManager(session).handle_subscription_webhook("customer.subscription.updated", event("price_shared"))
    assert sub.tier == SubscriptionTier.BASIC
    assert grant.credits_remaining == 1400
    assert not any(isinstance(x, CreditGrant) for x in session.added)


@pytest.mark.asyncio
async def test_enterprise_mapping_does_not_invent_an_unconfigured_credit_amount(configured_prices):
    sub, grant, session = setup_subscription()
    price = configured_prices["STRIPE_ENTERPRISE_PRICE_ID"]
    await SubscriptionManager(session).handle_subscription_webhook("customer.subscription.updated", event(price))
    assert sub.tier == SubscriptionTier.ENTERPRISE
    assert "enterprise" not in TIER_CREDIT_GRANTS_BY_ENUM
    assert grant.credits_remaining == 1400
    assert not any(isinstance(x, CreditGrant) for x in session.added)
