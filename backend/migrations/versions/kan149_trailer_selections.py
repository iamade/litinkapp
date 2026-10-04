"""add trailer selections table

Revision ID: kan149_trailer_selections
Revises: kan_458_add_scene_unit_type
Create Date: 2026-10-04 05:37:00.000000

KAN-149 AC1: select_highlight_scenes named surface persistence.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = 'kan149_trailer_selections'
down_revision = 'kan_458_add_scene_unit_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trailer_selections',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trailer_generation_id', pg.UUID(as_uuid=True), sa.ForeignKey('trailer_generations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('project_id', pg.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('source_scene_id', pg.UUID(as_uuid=True), sa.ForeignKey('trailer_scenes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('chapter_id', pg.UUID(as_uuid=True), nullable=True),
        sa.Column('artifact_id', pg.UUID(as_uuid=True), nullable=True),
        sa.Column('source_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('selection_order', sa.Integer(), nullable=False),
        sa.Column('scene_title', sa.String(), nullable=True),
        sa.Column('scene_description', sa.TEXT(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('start_time_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='6.0'),
        sa.Column('trailer_role', sa.String(), nullable=False),
        sa.Column('selection_reason', sa.TEXT(), nullable=True),
        sa.Column('selection_method', sa.String(), nullable=False, server_default='scored'),
        sa.Column('is_usable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('selection_metadata', pg.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_trailer_selections_trailer_generation_id', 'trailer_selections', ['trailer_generation_id'])
    op.create_index('ix_trailer_selections_project_id', 'trailer_selections', ['project_id'])
    op.create_index('ix_trailer_selections_source_scene_id', 'trailer_selections', ['source_scene_id'])
    op.create_index('ix_trailer_selections_chapter_id', 'trailer_selections', ['chapter_id'])
    op.create_index('ix_trailer_selections_artifact_id', 'trailer_selections', ['artifact_id'])
    op.create_index('ix_trailer_selections_generation_order', 'trailer_selections', ['trailer_generation_id', 'selection_order'])


def downgrade() -> None:
    op.drop_index('ix_trailer_selections_generation_order', table_name='trailer_selections')
    op.drop_index('ix_trailer_selections_artifact_id', table_name='trailer_selections')
    op.drop_index('ix_trailer_selections_chapter_id', table_name='trailer_selections')
    op.drop_index('ix_trailer_selections_source_scene_id', table_name='trailer_selections')
    op.drop_index('ix_trailer_selections_project_id', table_name='trailer_selections')
    op.drop_index('ix_trailer_selections_trailer_generation_id', table_name='trailer_selections')
    op.drop_table('trailer_selections')
