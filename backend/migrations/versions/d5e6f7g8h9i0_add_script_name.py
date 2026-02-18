"""add script_name

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2026-01-07 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d5e6f7g8h9i0"
down_revision: Union[str, None] = "c4d5e6f7g8h9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scripts", sa.Column("script_name", sa.String(), nullable=True))
    # Update existing scripts with default name "Unnamed Script" so they are consistent
    op.execute(
        "UPDATE scripts SET script_name = 'Unnamed Script' WHERE script_name IS NULL"
    )


def downgrade() -> None:
    op.drop_column("scripts", "script_name")
