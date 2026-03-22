"""add consultation_message_count to projects

Revision ID: x0y1z2a3b4c5
Revises: w9x0y1z2a3b4
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "x0y1z2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "w9x0y1z2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE projects
            ADD COLUMN IF NOT EXISTS consultation_message_count INTEGER NOT NULL DEFAULT 0;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE projects
            DROP COLUMN IF EXISTS consultation_message_count;
        """
    )
