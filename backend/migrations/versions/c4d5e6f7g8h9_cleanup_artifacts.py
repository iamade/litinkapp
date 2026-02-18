"""cleanup orphaned artifacts and enforce not null

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2026-01-07 13:58:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "c4d5e6f7g8h9"
down_revision = "b3c4d5e6f7g8"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Delete orphaned artifacts (where project_id is NULL)
    op.execute("DELETE FROM artifacts WHERE project_id IS NULL")

    # 2. Make project_id non-nullable
    op.alter_column("artifacts", "project_id", nullable=False)


def downgrade():
    # Make project_id nullable (revert)
    op.alter_column("artifacts", "project_id", nullable=True)
