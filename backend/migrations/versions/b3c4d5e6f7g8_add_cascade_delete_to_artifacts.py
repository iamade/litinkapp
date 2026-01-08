"""add cascade delete to artifacts

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-01-07 13:37:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7g8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    # Drop the old foreign key constraint
    op.drop_constraint("artifacts_project_id_fkey", "artifacts", type_="foreignkey")

    # Create new foreign key with CASCADE on delete
    op.create_foreign_key(
        "artifacts_project_id_fkey",
        "artifacts",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    # Drop the CASCADE foreign key
    op.drop_constraint("artifacts_project_id_fkey", "artifacts", type_="foreignkey")

    # Recreate without CASCADE
    op.create_foreign_key(
        "artifacts_project_id_fkey",
        "artifacts",
        "projects",
        ["project_id"],
        ["id"],
    )
