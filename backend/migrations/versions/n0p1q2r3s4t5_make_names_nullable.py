"""Make first_name and last_name nullable

Revision ID: n0p1q2r3s4t5
Revises: m9n0p1q2r3s4
Create Date: 2026-02-23 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "n0p1q2r3s4t5"
down_revision: Union[str, Sequence[str], None] = "m9n0p1q2r3s4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alter first_name to drop NOT NULL constraint
    op.alter_column(
        "user", "first_name", existing_type=sa.VARCHAR(length=30), nullable=True
    )
    # Alter last_name to drop NOT NULL constraint
    op.alter_column(
        "user", "last_name", existing_type=sa.VARCHAR(length=30), nullable=True
    )


def downgrade() -> None:
    # Cannot safely revert to NOT NULL if there are users with null names
    # but we can provide the statement for completeness
    pass
