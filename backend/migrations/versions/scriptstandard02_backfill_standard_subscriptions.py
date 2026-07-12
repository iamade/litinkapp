"""backfill Standard subscriptions from canonical Stripe price IDs

Revision ID: scriptstandard02
Revises: scriptstandard01
Create Date: 2026-07-12
"""

import os
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "scriptstandard02"
down_revision: Union[str, Sequence[str], None] = "scriptstandard01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRICE_ENV_NAMES = (
    "STRIPE_STANDARD_PRICE_ID",
    "STRIPE_STANDARD_MONTHLY_PRICE_ID",
    "STRIPE_STANDARD_ANNUAL_PRICE_ID",
)


def _standard_price_ids() -> list[str]:
    price_ids = [os.getenv(name) for name in PRICE_ENV_NAMES]
    configured = [price_id for price_id in price_ids if price_id]
    if not configured:
        raise RuntimeError(
            "Standard tier backfill requires STRIPE_STANDARD_PRICE_ID, "
            "STRIPE_STANDARD_MONTHLY_PRICE_ID, or "
            "STRIPE_STANDARD_ANNUAL_PRICE_ID"
        )
    if any(not re.fullmatch(r"price_[A-Za-z0-9_]+", value) for value in configured):
        raise RuntimeError("Standard tier price IDs have an invalid format")
    return list(dict.fromkeys(configured))


def upgrade() -> None:
    op.create_table(
        "subscription_tier_migration",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_subscription_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_tier", sa.Text(), nullable=False),
        sa.Column("new_tier", sa.Text(), nullable=False),
        sa.Column("stripe_price_id", sa.Text(), nullable=False),
        sa.Column("source_revision", sa.Text(), nullable=False),
        sa.Column(
            "migrated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "user_subscription_id",
            "source_revision",
            name="uq_subscription_tier_migration_revision",
        ),
    )

    price_ids = _standard_price_ids()
    quoted_price_ids = ", ".join(f"'{price_id}'" for price_id in price_ids)
    op.execute(
        sa.text(
            f"""
            INSERT INTO subscription_tier_migration (
                user_subscription_id,
                previous_tier,
                new_tier,
                stripe_price_id,
                source_revision
            )
            SELECT id, tier::text, 'standard', stripe_price_id, '{revision}'
            FROM user_subscriptions
            WHERE stripe_price_id IN ({quoted_price_ids})
              AND tier::text != 'standard'
            ON CONFLICT (user_subscription_id, source_revision) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE user_subscriptions
            SET tier = 'standard'::subscription_tier,
                updated_at = CURRENT_TIMESTAMP
            WHERE stripe_price_id IN ({quoted_price_ids})
              AND tier::text != 'standard'
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE user_subscriptions AS us
            SET tier = audit.previous_tier::subscription_tier,
                updated_at = CURRENT_TIMESTAMP
            FROM subscription_tier_migration AS audit
            WHERE audit.user_subscription_id = us.id
              AND audit.source_revision = :revision
            """
        ),
        {"revision": revision},
    )
    op.drop_table("subscription_tier_migration")
