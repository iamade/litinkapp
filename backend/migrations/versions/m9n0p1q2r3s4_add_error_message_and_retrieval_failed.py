"""add error_message column and retrieval_failed enum value

Revision ID: m9n0p1q2r3s4
Revises: l8m9n0p1q2r3
Create Date: 2026-02-09 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "m9n0p1q2r3s4"
down_revision: Union[str, Sequence[str], None] = "l8m9n0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add error_message column to video_generations
    op.add_column(
        "video_generations", sa.Column("error_message", sa.TEXT(), nullable=True)
    )
    # Add retrieval_failed to the video_generation_status enum
    op.execute(
        "ALTER TYPE video_generation_status ADD VALUE IF NOT EXISTS 'retrieval_failed'"
    )


def downgrade() -> None:
    op.drop_column("video_generations", "error_message")
    # Note: PostgreSQL cannot remove enum values; would need to recreate the enum
