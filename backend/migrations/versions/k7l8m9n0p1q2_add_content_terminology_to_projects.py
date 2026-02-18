"""Add content_terminology to projects

Revision ID: k7l8m9n0p1q2
Revises: j5k6l7m8n9o0
Create Date: 2026-01-27

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "k7l8m9n0p1q2"
down_revision = "j5k6l7m8n9o0"
branch_labels = None
depends_on = None


def upgrade():
    # Add content_terminology column to projects table
    op.add_column(
        "projects", sa.Column("content_terminology", sa.TEXT(), nullable=True)
    )


def downgrade():
    op.drop_column("projects", "content_terminology")
