"""add clean_file_url to merge_operations

Revision ID: z3b4c5d6e7f8
Revises: z2a3b4c5d6e7
Create Date: 2026-04-02

Adds clean_file_url column to merge_operations for storing
the unwatermarked version of videos (KAN-140).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "z3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "z2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE merge_operations
        ADD COLUMN IF NOT EXISTS clean_file_url VARCHAR DEFAULT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE merge_operations
        DROP COLUMN IF EXISTS clean_file_url
        """
    )
