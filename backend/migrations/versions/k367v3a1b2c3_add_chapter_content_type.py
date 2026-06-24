"""add chapter content_type for KAN-367 v3

Revision ID: k367v3a1b2c3
Revises: 240f2d0ba13d
Create Date: 2026-06-13 04:30:00.000000

"""

from alembic import op
from sqlalchemy import engine_from_config
from sqlalchemy.engine import reflection
import sqlalchemy as sa
from typing import Union, Sequence


def _has_column(table_name: str, column_name: str) -> bool:
    """Check whether a column exists in the target table."""
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    cols = {c['name'] for c in insp.get_columns(table_name)}
    return column_name in cols


def _column_is_nullable(table_name: str, column_name: str) -> bool:
    """Check whether a column is currently nullable."""
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    for c in insp.get_columns(table_name):
        if c['name'] == column_name:
            return c.get('nullable', True)
    return True

# revision identifiers, used by Alembic.
revision: str = 'k367v3a1b2c3'
down_revision: Union[str, Sequence[str], None] = '240f2d0ba13d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Idempotent migration: only add/alter columns that don't already exist or aren't
    # already nullable. This prevents collisions on Render production where some of these
    # columns may have been provisioned ahead of the migration record.
    if not _has_column('chapters', 'content_type'):
        op.add_column('chapters', sa.Column('content_type', sa.String(), nullable=False, server_default='chapter'))
    if not _has_column('chapters', 'order_index'):
        op.add_column('chapters', sa.Column('order_index', sa.Integer(), nullable=True))
    if _has_column('chapters', 'chapter_number') and not _column_is_nullable('chapters', 'chapter_number'):
        op.alter_column('chapters', 'chapter_number', existing_type=sa.Integer(), nullable=True)


def downgrade():
    if _has_column('chapters', 'chapter_number'):
        op.alter_column('chapters', 'chapter_number', existing_type=sa.Integer(), nullable=False)
    if _has_column('chapters', 'order_index'):
        op.drop_column('chapters', 'order_index')
    if _has_column('chapters', 'content_type'):
        op.drop_column('chapters', 'content_type')
