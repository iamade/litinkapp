"""add chapter content_type for KAN-367 v3

Revision ID: k367v3a1b2c3
Revises: 240f2d0ba13d
Create Date: 2026-06-13 04:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from typing import Union, Sequence

# revision identifiers, used by Alembic.
revision: str = 'k367v3a1b2c3'
down_revision: Union[str, Sequence[str], None] = '240f2d0ba13d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('chapters', sa.Column('content_type', sa.String(), nullable=False, server_default='chapter'))
    op.add_column('chapters', sa.Column('order_index', sa.Integer(), nullable=True))
    # Make chapter_number nullable (front_matter/back_matter items have no chapter_number)
    op.alter_column('chapters', 'chapter_number', existing_type=sa.Integer(), nullable=True)


def downgrade():
    op.alter_column('chapters', 'chapter_number', existing_type=sa.Integer(), nullable=False)
    op.drop_column('chapters', 'order_index')
    op.drop_column('chapters', 'content_type')
