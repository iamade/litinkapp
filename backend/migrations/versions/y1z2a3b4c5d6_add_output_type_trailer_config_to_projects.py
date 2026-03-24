"""add output_type and trailer_config to projects

Revision ID: y1z2a3b4c5d6
Revises: x0y1z2a3b4c5
Create Date: 2026-03-24 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "y1z2a3b4c5d6"
down_revision: Union[str, None] = "x0y1z2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "output_type",
            sa.VARCHAR(30),
            server_default=sa.text("'full_production'"),
            nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "trailer_config",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "trailer_config")
    op.drop_column("projects", "output_type")
