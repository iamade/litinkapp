"""add user_downloads table for download tracking

Revision ID: z2a3b4c5d6e7
Revises: y1z2a3b4c5d6
Create Date: 2026-03-31

Adds user_downloads table to track daily downloads per user
for tier-based download restrictions (KAN-141).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "z2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "y1z2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_downloads (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            merge_id UUID,
            resource_type VARCHAR NOT NULL DEFAULT 'merge',
            downloaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_downloads_user_id
            ON user_downloads (user_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_downloads_downloaded_at
            ON user_downloads (downloaded_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_downloads_downloaded_at")
    op.execute("DROP INDEX IF EXISTS ix_user_downloads_user_id")
    op.execute("DROP TABLE IF EXISTS user_downloads")
