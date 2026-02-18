"""Add cinematic universe fields to artifacts

Revision ID: j5k6l7m8n9o0
Revises: 6853163b0db2
Create Date: 2026-01-27

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "j5k6l7m8n9o0"
down_revision = "6853163b0db2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new fields to artifacts table for script/cinematic universe tracking
    op.add_column("artifacts", sa.Column("source_file_url", sa.String(), nullable=True))
    op.add_column(
        "artifacts",
        sa.Column("is_script", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("artifacts", sa.Column("script_order", sa.Integer(), nullable=True))
    op.add_column(
        "artifacts", sa.Column("content_type_label", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("artifacts", "content_type_label")
    op.drop_column("artifacts", "script_order")
    op.drop_column("artifacts", "is_script")
    op.drop_column("artifacts", "source_file_url")
