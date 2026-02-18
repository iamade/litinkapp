"""add character image generation columns

Revision ID: add_char_img_cols_001
Revises:
Create Date: 2026-01-07

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_char_img_cols_001"
down_revision = "d5e6f7g8h9i0"  # Points to add_script_name migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add image generation status and tracking columns to characters table
    op.add_column(
        "characters", sa.Column("image_generation_status", sa.String(), nullable=True)
    )
    op.add_column(
        "characters", sa.Column("image_generation_task_id", sa.String(), nullable=True)
    )
    op.add_column(
        "characters", sa.Column("generation_method", sa.String(), nullable=True)
    )
    op.add_column("characters", sa.Column("model_used", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("characters", "model_used")
    op.drop_column("characters", "generation_method")
    op.drop_column("characters", "image_generation_task_id")
    op.drop_column("characters", "image_generation_status")
