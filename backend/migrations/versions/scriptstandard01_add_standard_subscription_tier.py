"""add standard subscription tier

Revision ID: scriptstandard01
Revises: kan395rights01
Create Date: 2026-07-12
"""

from typing import Sequence, Union

from alembic import op

revision: str = "scriptstandard01"
down_revision: Union[str, Sequence[str], None] = "kan395rights01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL enum additions must be committed before the value is used by
    # the following backfill revision on older supported PostgreSQL versions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE subscription_tier ADD VALUE IF NOT EXISTS 'standard'")


def downgrade() -> None:
    # PostgreSQL does not support dropping one enum value safely in place.
    pass
