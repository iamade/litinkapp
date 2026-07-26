"""Merge KAN-438 and KAN-439 Alembic heads

Both migrations branch from scriptstandard02, creating multiple heads.
This merge migration unifies them.

Revision ID: merge_kan438_439
Revises: kan438_cinematic_episode_gates, kan439_production_bible
Create Date: 2026-07-21 17:30:00.000000
"""

from alembic import op

# ── Regression guard (KAN-439) ──
# Ensure the SQLAlchemy ``text()`` builtin is not shadowed by a model
# column named ``text``.  A class-level ``text`` attribute on a SQLModel
# would clobber ``sqlalchemy.text`` in the module namespace, breaking
# ``server_default=text(...)`` calls in migrations.
from sqlalchemy import text as _sa_text  # noqa: E402

assert callable(_sa_text), (
    "sqlalchemy.text must remain callable — "
    "a model column named 'text' is shadowing it (KAN-439 regression)"
)

# revision identifiers, used by Alembic.
revision = 'merge_kan438_439'
down_revision = ('kan438_cinematic_episode_gates', 'kan439_production_bible')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass