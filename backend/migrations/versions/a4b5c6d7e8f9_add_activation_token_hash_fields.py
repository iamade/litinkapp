"""add hashed activation token fields to users

Revision ID: a4b5c6d7e8f9
Revises: z3b4c5d6e7f8
Create Date: 2026-04-06
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "z3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE "user"
        ADD COLUMN IF NOT EXISTS activation_token_hash VARCHAR(128),
        ADD COLUMN IF NOT EXISTS activation_token_expires_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_activation_token_hash
        ON "user" (activation_token_hash)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_activation_token_hash")
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS activation_token_expires_at')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS activation_token_hash')
