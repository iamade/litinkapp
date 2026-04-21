"""add trailer tables

Revision ID: a1b2c3d4e5f6
Revises: z3b4c5d6e7f8
Create Date: 2026-04-13 14:10:00.000000

KAN-149: Trailer Engine — AI scene selection service
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'z3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create Enums
    trailer_status_enum = sa.Enum(
        'ANALYZING', 'SCENES_SELECTED', 'SCRIPT_GENERATING', 'SCRIPT_READY',
        'AUDIO_GENERATING', 'AUDIO_READY', 'ASSEMBLING', 'COMPLETED', 'FAILED',
        name='trailer_status',
        create_type=False,
    )
    trailer_status_enum.create(op.get_bind(), checkfirst=True)
    
    selection_method_enum = sa.Enum(
        'AI_AUTO', 'USER_MANUAL', 'AI_SUGGESTED_USER_APPROVED',
        name='selection_method',
        create_type=False,
    )
    selection_method_enum.create(op.get_bind(), checkfirst=True)
    
    # Create trailer_generations table
    op.create_table(
        'trailer_generations',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', pg.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('"user".id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_duration_seconds', sa.Integer, nullable=False, server_default='90'),
        sa.Column('tone', sa.String(50), nullable=False, server_default='epic'),
        sa.Column('style', sa.String(50), nullable=False, server_default='cinematic'),
        sa.Column('status', sa.Enum('ANALYZING', 'SCENES_SELECTED', 'SCRIPT_GENERATING', 'SCRIPT_READY', 'AUDIO_GENERATING', 'AUDIO_READY', 'ASSEMBLING', 'COMPLETED', 'FAILED', name='trailer_status', create_type=False), nullable=False, server_default='ANALYZING'),
        sa.Column('selection_method', sa.Enum('AI_AUTO', 'USER_MANUAL', 'AI_SUGGESTED_USER_APPROVED', name='selection_method', create_type=False), nullable=False, server_default='AI_AUTO'),
        sa.Column('trailer_script', sa.TEXT, nullable=True),
        sa.Column('narration_text', sa.TEXT, nullable=True),
        sa.Column('narration_audio_url', sa.String(500), nullable=True),
        sa.Column('video_url', sa.String(500), nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('total_scenes_analyzed', sa.Integer, nullable=False, server_default='0'),
        sa.Column('scenes_selected_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('actual_duration_seconds', sa.Integer, nullable=True),
        sa.Column('credits_used', sa.Integer, nullable=False, server_default='0'),
        sa.Column('error_message', sa.TEXT, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    
    # Create trailer_scenes table
    op.create_table(
        'trailer_scenes',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trailer_generation_id', pg.UUID(as_uuid=True), sa.ForeignKey('trailer_generations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('chapter_id', pg.UUID(as_uuid=True), nullable=True),
        sa.Column('artifact_id', pg.UUID(as_uuid=True), nullable=True),
        sa.Column('scene_number', sa.Integer, nullable=False),
        sa.Column('scene_title', sa.String(200), nullable=True),
        sa.Column('scene_description', sa.TEXT, nullable=True),
        sa.Column('action_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('emotional_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('visual_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('narrative_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('overall_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('is_selected', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('selection_reason', sa.TEXT, nullable=True),
        sa.Column('start_time_seconds', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('duration_seconds', sa.Float, nullable=False, server_default='5.0'),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('video_url', sa.String(500), nullable=True),
        sa.Column('audio_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes
    op.create_index('ix_trailer_generations_project_id', 'trailer_generations', ['project_id'])
    op.create_index('ix_trailer_generations_user_id', 'trailer_generations', ['user_id'])
    op.create_index('ix_trailer_scenes_trailer_generation_id', 'trailer_scenes', ['trailer_generation_id'])


def downgrade() -> None:
    op.drop_index('ix_trailer_scenes_trailer_generation_id', 'trailer_scenes')
    op.drop_index('ix_trailer_generations_user_id', 'trailer_generations')
    op.drop_index('ix_trailer_generations_project_id', 'trailer_generations')
    
    op.drop_table('trailer_scenes')
    op.drop_table('trailer_generations')
    
    # Drop Enums
    op.execute("DROP TYPE IF EXISTS selection_method")
    op.execute("DROP TYPE IF EXISTS trailer_status")