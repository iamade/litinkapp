"""add marketing to project_type enum

Revision ID: m5a6r7k8e9t0
Revises: kan_458_add_scene_unit_type
Create Date: 2026-10-10

KAN-147: the AI consultation contract resolves project_type from the
canonical union entertainment|training|marketing; add the matching
MARKETING member to the native project_type enum (labels are enum member
names, per the initial 66a1aa9f0f52 migration).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m5a6r7k8e9t0"
down_revision: Union[str, Sequence[str], None] = "kan_458_add_scene_unit_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'MARKETING' to the native project_type enum."""
    op.execute("ALTER TYPE project_type ADD VALUE IF NOT EXISTS 'MARKETING'")


def downgrade() -> None:
    """Downgrade - PostgreSQL cannot remove enum values directly."""
    pass
