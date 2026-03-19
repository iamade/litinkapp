"""add credit_failures table

Revision ID: v8w9x0y1z2a3
Revises: u7v8w9x0y1z2
Create Date: 2026-03-18

Adds the credit_failures table for tracking failed confirm_deduction calls
so that the reconcile_failed_credits Celery task can retry them (KAN-119).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "v8w9x0y1z2a3"
down_revision: Union[str, Sequence[str], None] = "u7v8w9x0y1z2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_failures (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL,
            reservation_id  UUID NOT NULL,
            amount          INTEGER NOT NULL,
            operation_type  VARCHAR NOT NULL,
            error_message   TEXT,
            status          VARCHAR NOT NULL DEFAULT 'pending',
            retry_count     INTEGER NOT NULL DEFAULT 0,
            created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at     TIMESTAMP WITH TIME ZONE
        );
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_credit_failures_user_id "
        "ON credit_failures (user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_credit_failures_status "
        "ON credit_failures (status);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS credit_failures;")
