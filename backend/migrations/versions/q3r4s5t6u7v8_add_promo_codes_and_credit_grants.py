"""add promo_codes and credit_grants tables

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-03-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "q3r4s5t6u7v8"
down_revision: Union[str, Sequence[str], None] = "p2q3r4s5t6u7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create grant_type enum
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'grant_type') THEN
                CREATE TYPE grant_type AS ENUM ('promo', 'purchase', 'free_tier');
            END IF;
        END$$;
        """
    )

    # Create promo_codes table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS promo_codes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code VARCHAR(64) NOT NULL UNIQUE,
            credit_amount INTEGER NOT NULL,
            expiry_days INTEGER NOT NULL,
            max_redemptions INTEGER NOT NULL,
            current_redemptions INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by UUID,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_promo_codes_code ON promo_codes (code);")

    # Create credit_grants table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_grants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            credits_remaining INTEGER NOT NULL,
            credits_used INTEGER NOT NULL DEFAULT 0,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            promo_code_id UUID REFERENCES promo_codes(id) ON DELETE SET NULL,
            grant_type grant_type NOT NULL DEFAULT 'promo',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_credit_grants_user_id ON credit_grants (user_id);"
    )

    # Seed the first promo code: BVCBETA2026
    op.execute(
        """
        INSERT INTO promo_codes (code, credit_amount, expiry_days, max_redemptions, is_active)
        VALUES ('BVCBETA2026', 5000, 60, 10, TRUE)
        ON CONFLICT (code) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS credit_grants;")
    op.execute("DROP TABLE IF EXISTS promo_codes;")
    op.execute("DROP TYPE IF EXISTS grant_type;")
