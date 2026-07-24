"""merge kan438 kan439

Revision ID: merge_kan438_439
Revises: kan438_cinematic_episode_gates, kan439_production_bible
Create Date: 2026-07-24 14:29:37.648049

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'merge_kan438_439'
down_revision: Union[str, Sequence[str], None] = ('kan438_cinematic_episode_gates', 'kan439_production_bible')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
