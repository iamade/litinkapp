"""add updated_at and model_id to image_generations

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-03-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "p2q3r4s5t6u7"
down_revision: Union[str, Sequence[str], None] = "o1p2q3r4s5t6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing updated_at and model_id columns to image_generations."""
    op.add_column(
        "image_generations",
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "image_generations",
        sa.Column("model_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Remove updated_at and model_id columns from image_generations."""
    op.drop_column("image_generations", "model_id")
    op.drop_column("image_generations", "updated_at")
