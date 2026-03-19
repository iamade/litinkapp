"""add credit_transactions table

Revision ID: u7v8w9x0y1z2
Revises: t6u7v8w9x0y1
Create Date: 2026-03-18

Adds the credit_transactions table used by the credit deduction middleware
(KAN-119). All enum-like columns use plain VARCHAR to avoid the ENUM cast
issues encountered in prior migrations.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "u7v8w9x0y1z2"
down_revision: Union[str, Sequence[str], None] = "t6u7v8w9x0y1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL,
            amount          INTEGER NOT NULL,
            status          VARCHAR NOT NULL DEFAULT 'reserved',
            operation_type  VARCHAR NOT NULL,
            ref_id          VARCHAR,
            parent_id       UUID,
            meta            JSONB,
            created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at      TIMESTAMP WITH TIME ZONE
        );
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_credit_transactions_user_id "
        "ON credit_transactions (user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_credit_transactions_status "
        "ON credit_transactions (status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_credit_transactions_operation_type "
        "ON credit_transactions (operation_type);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_credit_transactions_ref_id "
        "ON credit_transactions (ref_id);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS credit_transactions;")
