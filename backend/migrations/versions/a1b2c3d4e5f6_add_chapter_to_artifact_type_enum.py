"""add_chapter_to_artifact_type_enum

Revision ID: a1b2c3d4e5f6
Revises: 66a1aa9f0f52
Create Date: 2025-12-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "7ebcb2766008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'chapter' value to artifact_type enum."""
    # PostgreSQL requires ALTER TYPE to add new enum values
    # We need to add both lowercase 'chapter' (used by Python code)
    # and optionally uppercase for consistency
    op.execute("ALTER TYPE artifact_type ADD VALUE IF NOT EXISTS 'chapter'")


def downgrade() -> None:
    """Downgrade - cannot easily remove enum values in PostgreSQL."""
    # PostgreSQL doesn't support removing enum values directly
    # Would need to recreate the enum type, which is complex
    pass
