"""KAN-503: tier changes must ADJUST existing credit grants, and cancellation
must FREEZE the credit balance.

Defect (LC first-party verification at dev cba36243):
  - checkout.session.completed (handle_subscription_webhook) creates a NEW
    CreditGrant unconditionally, so buying a different tier STACKS a new grant
    on top of the live one instead of adjusting it.
  - cancel_subscription and the subscription.deleted webhook never touch
    grants; get_raw_balance (credits/service.py) sums non-expired grants with
    no subscription-status term, so a cancelled user's balance keeps counting
    to the full 365-day grant expiry.

Semantics chosen (documented for LC adjudication):
  - Tier change ADJUSTS the live subscription grant by the delta between the
    old and new tier's grant amounts (TIER_CREDIT_GRANTS_BY_ENUM), clamped at
    0. No cash proration is invented. A pristine balance therefore moves
    exactly to the new tier's amount.
  - Cancellation FREEZES by capping the live grant's expires_at at the paid
    period end (or now for an immediate cancel): the balance stays usable
    through the period the user paid for, then lapses, and never accrues past
    the cancellation.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("STRIPE_SECRET_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "test@litinkai.dev")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import pytest  # noqa: E402

from app.api.services.subscription import SubscriptionManager  # noqa: E402
from app.subscriptions.models import SubscriptionStatus  # noqa: E402
from app.credits.service import CreditService  # noqa: E402
from app.promo.models import CreditGrant, GrantType  # noqa: E402


NOW = datetime.now(timezone.utc)

pytestmark = pytest.mark.asyncio


class _Result:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value

    def all(self):
        return list(self._value) if isinstance(self._value, (list, tuple)) else ([self._value] if self._value else [])

    def one(self):
        return self._value


class _DispatchingSession:
    """Dispatch exec() on SQL text: subscriptions, credit_grants, users."""

    def __init__(self, subscription=None, grants=None, user=None):
        self.subscription = subscription
        self.grants = list(grants or [])
        self.user = user
        self.added = []
        self.committed = 0

    async def exec(self, statement):
        text = str(statement)
        t = text.lower()
        if "credit_grants" in t:
            if "sum(" in t:
                # emulate the SQL aggregate the real DB would compute
                total = sum(
                    g.credits_remaining for g in self.grants
                    if g.expires_at > datetime.now(timezone.utc)
                    and g.credits_remaining > 0
                )
                return _Result(total)
            return _Result(self.grants)
        t = text.lower()
        if "usersubscription" in t or "user_subscription" in t:
            return _Result(self.subscription)
        if '"user"' in t or "from user" in t:
            return _Result(self.user)
        return _Result(None)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed += 1

    async def refresh(self, item):
        return item

    async def rollback(self):
        pass


def _grant(remaining, expires_at=None, grant_type=GrantType.PURCHASE.value):
    return CreditGrant(
        user_id=uuid.uuid4(),
        credits_remaining=remaining,
        credits_used=0,
        expires_at=expires_at or (NOW + timedelta(days=365)),
        promo_code_id=None,
        grant_type=grant_type,
    )


def _subscription(tier, status=None):
    sub = MagicMock()
    sub.user_id = uuid.uuid4()
    sub.id = uuid.uuid4()
    sub.tier = tier
    sub.status = status or SubscriptionStatus.ACTIVE
    sub.cancel_at_period_end = False
    sub.stripe_subscription_id = "sub_test_123"
    sub.stripe_customer_id = "cus_test_123"
    sub.stripe_price_id = "price_old"
    sub.current_period_start = NOW - timedelta(days=10)
    sub.current_period_end = NOW + timedelta(days=20)
    sub.cancelled_at = None
    sub.updated_at = None
    return sub


def _checkout_event(tier_value):
    return {
        "type": "checkout.session.completed",
        "object": {
            "customer": "cus_test_123",
            "subscription": "sub_test_123",
            "metadata": {"user_id": str(uuid.uuid4()), "tier": tier_value},
        },
    }


async def _run_checkout(session, tier_value):
    svc = SubscriptionManager(session)
    with patch.object(
        SubscriptionManager, "_send_payment_confirmation_email", AsyncMock()
    ):
        await svc.handle_subscription_webhook(
            "checkout.session.completed",
            {"object": {"customer": "cus_test_123", "subscription": "sub_test_123",
                        "metadata": {"user_id": str(session.subscription.user_id), "tier": tier_value}}},
        )


class TestTierChange:
    async def test_upgrade_adjusts_existing_grant_not_stacked(self):
        from app.api.services.subscription import SubscriptionTier

        sub = _subscription(SubscriptionTier.BASIC)
        grant = _grant(1500)
        session = _DispatchingSession(subscription=sub, grants=[grant], user=MagicMock())
        await _run_checkout(session, "premium")
        assert grant.credits_remaining == 13100, (
            "upgrade must adjust the live grant to basic(1500) + delta(13100-1500)"
        )
        new_grants = [
            a for a in session.added
            if isinstance(a, CreditGrant) and a is not grant
        ]
        assert new_grants == [], "upgrade must NOT add a new grant on top"

    async def test_downgrade_adjusts_existing_grant(self):
        from app.api.services.subscription import SubscriptionTier

        sub = _subscription(SubscriptionTier.PREMIUM)
        grant = _grant(13100)
        session = _DispatchingSession(subscription=sub, grants=[grant], user=MagicMock())
        await _run_checkout(session, "basic")
        assert grant.credits_remaining == 1500, (
            "downgrade must adjust the live grant to premium(13100) + delta(1500-13100)"
        )
        new_grants = [
            a for a in session.added
            if isinstance(a, CreditGrant) and a is not grant
        ]
        assert new_grants == []

    async def test_first_subscribe_still_creates_grant(self):
        from app.api.services.subscription import SubscriptionTier

        sub = _subscription(SubscriptionTier.FREE)
        session = _DispatchingSession(subscription=sub, grants=[], user=MagicMock())
        await _run_checkout(session, "basic")
        new_grants = [a for a in session.added if isinstance(a, CreditGrant)]
        assert len(new_grants) == 1 and new_grants[0].credits_remaining == 1500


class TestCancelFreeze:
    async def test_immediate_cancel_freezes_grant_now(self):
        grant = _grant(1500)
        sub = _subscription(None)
        session = _DispatchingSession(subscription=sub, grants=[grant], user=MagicMock())
        svc = SubscriptionManager(session)
        with patch(
            "app.api.services.subscription.stripe_service"
        ) as stripe_mock:
            stripe_mock.cancel_subscription = AsyncMock(
                return_value={
                    "subscription_id": sub.stripe_subscription_id,
                    "status": "cancelled",
                    "cancel_at_period_end": False,
                    "current_period_end": None,
                }
            )
            await svc.cancel_subscription(sub.user_id, immediate=True)
        assert grant.expires_at <= datetime.now(timezone.utc), (
            "immediate cancel must freeze the grant at cancel time"
        )

    async def test_cancel_at_period_end_freezes_at_period_end(self):
        grant = _grant(1500)
        sub = _subscription(None)
        period_end = NOW + timedelta(days=20)
        session = _DispatchingSession(subscription=sub, grants=[grant], user=MagicMock())
        svc = SubscriptionManager(session)
        with patch(
            "app.api.services.subscription.stripe_service"
        ) as stripe_mock:
            stripe_mock.cancel_subscription = AsyncMock(
                return_value={
                    "subscription_id": sub.stripe_subscription_id,
                    "status": "active",
                    "cancel_at_period_end": True,
                    "current_period_end": int(period_end.timestamp()),
                }
            )
            await svc.cancel_subscription(sub.user_id, immediate=False)
        assert grant.expires_at <= period_end + timedelta(seconds=1), (
            "cancel at period end must freeze the grant no later than the paid period end"
        )
        assert grant.expires_at > datetime.now(timezone.utc), (
            "the paid-for balance stays usable through the period end"
        )

    async def test_deleted_webhook_freezes_grants(self):
        grant = _grant(1500)
        sub = _subscription(None)
        period_end = NOW + timedelta(days=20)
        sub.current_period_end = period_end
        session = _DispatchingSession(subscription=sub, grants=[grant], user=MagicMock())
        svc = SubscriptionManager(session)
        await svc.sync_subscription_from_stripe_event(
            "customer.subscription.deleted",
            {
                "id": sub.stripe_subscription_id,
                "status": "canceled",
                "current_period_end": int(period_end.timestamp()),
            },
        )
        assert grant.expires_at <= period_end + timedelta(seconds=1), (
            "the deleted webhook must freeze live grants at the period end"
        )


class TestRawBalanceRespectsFreeze:
    async def test_frozen_grant_stops_counting_after_cap(self):
        frozen = _grant(1500, expires_at=NOW - timedelta(seconds=1))
        user_id = frozen.user_id
        session = _DispatchingSession(subscription=None, grants=[frozen])
        session.exec_grants_for = user_id
        credits = CreditService(session)
        balance = await credits.get_raw_balance(user_id)
        assert balance == 0, "an expired (frozen) grant must not count toward the balance"
