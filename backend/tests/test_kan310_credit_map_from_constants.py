"""KAN-310: the pricing card credit counts must come from the backend constants.

The frontend pricing card used to carry its own hardcoded tier -> credits map
(frontend/src/components/Subscription/SubscriptionTierCard.tsx). That let the
card and backend/app/credits/constants.py drift apart silently.

This file pins the chain:
    app/credits/constants.py  ->  GET /api/v1/subscriptions/tiers  ->  pricing card

and adds the disagreement test LC asked for: it FAILS if the card and the
constants ever disagree, in either direction.

Scope: credit counts only. Prices are out of scope (Ade decides on Basic).
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("STRIPE_SECRET_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "test@litinkai.dev")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")

from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
CARD_PATH = REPO_ROOT / "frontend/src/components/Subscription/SubscriptionTierCard.tsx"

# Stripe product key -> SubscriptionTier enum value.
# TIER_CREDIT_GRANTS_BY_ENUM additionally carries a legacy "pro": 4800 alias.
STRIPE_KEY_TO_TIER = {
    "FREE": "free",
    "BASIC": "basic",
    "STANDARD": "standard",
    "PREMIUM": "premium",
    "PRO": "professional",
}


def _read_card_source() -> str:
    return CARD_PATH.read_text(encoding="utf-8")


class TestTierCreditsServedFromConstants:
    """The /tiers endpoint must serve credits straight from the constants."""

    @pytest.mark.asyncio
    async def test_served_monthly_credits_match_constants_for_every_tier(self):
        from app.api.routes.subscriptions.routes import get_subscription_tiers
        from app.credits.constants import TIER_CREDIT_GRANTS_BY_ENUM

        served = await get_subscription_tiers(session=MagicMock())
        assert served, "/tiers returned no tiers"

        for tier_info in served:
            tier = tier_info["tier"]
            expected = TIER_CREDIT_GRANTS_BY_ENUM.get(tier)
            assert tier_info["monthly_credits"] == expected, (
                f"{tier}: served {tier_info['monthly_credits']!r} but constants say "
                f"{expected!r}"
            )

    def test_legacy_pro_alias_is_not_swapped_with_professional(self):
        """The enum map legacy "pro" entry must reach the card unchanged.

        "pro" is 4800 in TIER_CREDIT_GRANTS_BY_ENUM (legacy Standard value),
        while the Stripe-name map "PRO" is 33100 and belongs to "professional".
        The two must not be swapped.
        """
        from app.credits.constants import TIER_CREDIT_GRANTS_BY_ENUM

        assert TIER_CREDIT_GRANTS_BY_ENUM["pro"] == 4800
        assert TIER_CREDIT_GRANTS_BY_ENUM["professional"] == 33100

    def test_stripe_name_map_and_enum_map_agree(self):
        """Changing one constants map without the other is a disagreement."""
        from app.credits.constants import (
            TIER_CREDIT_GRANTS,
            TIER_CREDIT_GRANTS_BY_ENUM,
        )

        for stripe_key, tier_value in STRIPE_KEY_TO_TIER.items():
            assert tier_value in TIER_CREDIT_GRANTS_BY_ENUM, (
                f"{stripe_key} -> {tier_value} missing from TIER_CREDIT_GRANTS_BY_ENUM"
            )
            assert TIER_CREDIT_GRANTS[stripe_key] == TIER_CREDIT_GRANTS_BY_ENUM[tier_value], (
                f"{stripe_key}: TIER_CREDIT_GRANTS has "
                f"{TIER_CREDIT_GRANTS[stripe_key]} but TIER_CREDIT_GRANTS_BY_ENUM"
                f"[{tier_value!r}] has {TIER_CREDIT_GRANTS_BY_ENUM[tier_value]}"
            )

    def test_enterprise_has_no_monthly_credit_grant(self):
        """Enterprise is served without a credit count; the card renders Unlimited."""
        from app.credits.constants import TIER_CREDIT_GRANTS_BY_ENUM

        assert "enterprise" not in TIER_CREDIT_GRANTS_BY_ENUM


class TestCardCannotDisagreeWithConstants:
    """THE DISAGREEMENT TEST (LC's ask).

    Fails when the pricing card hardcodes credit amounts again, because a
    hardcoded map is exactly how the card and the constants drift apart.
    """

    def test_card_contains_no_hardcoded_credit_map(self):
        card = _read_card_source()

        assert "TIER_CREDITS" not in card, (
            "The pricing card must not carry a hardcoded tier -> credits map; "
            "credits come from the backend (KAN-310)."
        )

        hardcoded_amounts = re.findall(r'amount:\s*"[\d,]+"', card)
        assert not hardcoded_amounts, (
            f"The pricing card hardcodes credit amount(s) {hardcoded_amounts}; "
            "credits must be served from app/credits/constants.py (KAN-310)."
        )

        quoted_numbers = re.findall(r'"[\d,]+"', card)
        assert not quoted_numbers, (
            f"The pricing card contains quoted numeric literal(s) {quoted_numbers}; "
            "any credit amount there is a hardcoded value that can disagree with "
            "the backend constants (KAN-310)."
        )

    def test_card_reads_credits_from_the_served_tier(self):
        card = _read_card_source()

        assert "monthly_credits" in card, (
            "The pricing card must render the credit count served on the tier "
            "object (monthly_credits), not a local map (KAN-310)."
        )

    def test_no_credit_count_literal_from_the_constants_leaks_into_the_card(self):
        """Belt-and-braces: none of the served credit values may appear as a
        literal in the card source."""
        from app.credits.constants import TIER_CREDIT_GRANTS_BY_ENUM

        card = _read_card_source()
        for tier, amount in TIER_CREDIT_GRANTS_BY_ENUM.items():
            for literal in (f'"{amount}"', f'"{amount:,}"'):
                assert literal not in card, (
                    f"The pricing card contains the literal {literal} for tier "
                    f"{tier!r}; the card must not hardcode credit amounts (KAN-310)."
                )
