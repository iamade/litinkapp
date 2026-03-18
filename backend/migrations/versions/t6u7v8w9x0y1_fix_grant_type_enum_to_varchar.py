"""fix_grant_type_enum_to_varchar

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-03-17

Root cause:
  The `grant_type` column on the credit_grants table was created with a
  PostgreSQL ENUM type (grant_type) in migration q3r4s5t6u7v8.

  The SQLModel definition uses pg.ENUM(GrantType, name="grant_type") which
  causes SQLAlchemy to pass the Python enum *name* (e.g. "FREE_TIER") instead
  of the enum *value* (e.g. "free_tier") to Postgres.  The DB enum only
  accepts the lowercase values, so every INSERT fails with:
      invalid input value for enum grant_type: "FREE_TIER"

  This is the same class of bug fixed for account_status (s5t6u7v8w9x0) and
  security_question (r4s5t6u7v8w9) on the user table.

Fix: convert the column to plain VARCHAR and drop the stale ENUM type.
     The Python GrantType enum is kept for business-logic validation only.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "t6u7v8w9x0y1"
down_revision: Union[str, Sequence[str], None] = "s5t6u7v8w9x0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast current ENUM values to text, then to varchar.
    op.execute(
        "ALTER TABLE credit_grants ALTER COLUMN grant_type "
        "TYPE VARCHAR USING grant_type::text"
    )
    # Drop the now-unused ENUM type.
    op.execute("DROP TYPE IF EXISTS grant_type")


def downgrade() -> None:
    # Recreate the enum and convert the column back (best-effort).
    op.execute(
        "CREATE TYPE grant_type AS ENUM ('promo', 'purchase', 'free_tier')"
    )
    op.execute(
        "ALTER TABLE credit_grants ALTER COLUMN grant_type "
        "TYPE grant_type USING grant_type::grant_type"
    )
