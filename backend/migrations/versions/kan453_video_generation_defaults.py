"""add database defaults for video generation retry state

Revision ID: kan453_video_defaults
Revises: kan_458_add_scene_unit_type
Create Date: 2026-10-18
"""
from alembic import op
import sqlalchemy as sa

revision = "kan453_video_defaults"
down_revision = "kan_458_add_scene_unit_type"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column("video_generations", "can_resume", existing_type=sa.Boolean(), server_default=sa.text("false"), existing_nullable=False)
    op.alter_column("video_generations", "retry_count", existing_type=sa.Integer(), server_default=sa.text("0"), existing_nullable=False)

def downgrade() -> None:
    op.alter_column("video_generations", "retry_count", existing_type=sa.Integer(), server_default=None, existing_nullable=False)
    op.alter_column("video_generations", "can_resume", existing_type=sa.Boolean(), server_default=None, existing_nullable=False)
