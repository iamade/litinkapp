"""KAN-438: Cinematic dialogue episode gate models

Creates tables: sequence_units, line_tracking, shot_diversity_reports,
continuity_references — for cinematic dialogue episode gate tracking.

Revision ID: kan438_cinematic_episode_gates
Revises: scriptstandard02
Create Date: 2026-07-21 17:01:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = 'kan438_cinematic_episode_gates'
down_revision = 'scriptstandard02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Create ENUM types ---
    sequence_unit_type_enum = pg.ENUM(
        'ident_title', 'prologue', 'dialogue_act', 'climax_resolution',
        'closing_bookend', 'end_title_credits',
        name='sequence_unit_type',
        create_type=False,
    )
    sequence_unit_type_enum.create(op.get_bind(), checkfirst=True)

    sequence_unit_status_enum = pg.ENUM(
        'pending', 'active', 'completed', 'skipped',
        name='sequence_unit_status',
        create_type=False,
    )
    sequence_unit_status_enum.create(op.get_bind(), checkfirst=True)

    line_tracking_status_enum = pg.ENUM(
        'unassigned', 'character_assigned', 'voice_assigned', 'scene_assigned',
        'shot_assigned', 'audio_generated', 'lipsync_queued', 'lipsync_complete',
        'placed',
        name='line_tracking_status',
        create_type=False,
    )
    line_tracking_status_enum.create(op.get_bind(), checkfirst=True)

    shot_diversity_report_status_enum = pg.ENUM(
        'pending', 'analyzing', 'completed', 'failed',
        name='shot_diversity_report_status',
        create_type=False,
    )
    shot_diversity_report_status_enum.create(op.get_bind(), checkfirst=True)

    continuity_reference_type_enum = pg.ENUM(
        'character', 'world', 'prop', 'location',
        name='continuity_reference_type',
        create_type=False,
    )
    continuity_reference_type_enum.create(op.get_bind(), checkfirst=True)

    # --- Create sequence_units table ---
    op.create_table(
        'sequence_units',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_generation_id', pg.UUID(as_uuid=True),
                  sa.ForeignKey('video_generations.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('unit_type', sequence_unit_type_enum, nullable=False),
        sa.Column('unit_order', sa.Integer, nullable=False),
        sa.Column('title', sa.String, nullable=False),
        sa.Column('script_content', sa.TEXT, nullable=True),
        sa.Column('duration_seconds', sa.Float, nullable=True),
        sa.Column('status', sequence_unit_status_enum, nullable=False, server_default='pending'),
        sa.Column('metadata', pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_sequence_units_video_generation_id', 'sequence_units', ['video_generation_id'])

    # --- Create line_tracking table ---
    op.create_table(
        'line_tracking',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('sequence_unit_id', pg.UUID(as_uuid=True),
                  sa.ForeignKey('sequence_units.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('video_generation_id', pg.UUID(as_uuid=True),
                  sa.ForeignKey('video_generations.id'),
                  nullable=False),
        sa.Column('line_text', sa.TEXT, nullable=False),
        sa.Column('character_name', sa.String, nullable=True),
        sa.Column('voice_id', sa.String, nullable=True),
        sa.Column('scene_id', sa.String, nullable=True),
        sa.Column('shot_id', sa.String, nullable=True),
        sa.Column('source_audio_url', sa.String, nullable=True),
        sa.Column('lipsync_task_id', sa.String, nullable=True),
        sa.Column('resolved_provider', sa.String, nullable=True),
        sa.Column('resolved_model', sa.String, nullable=True),
        sa.Column('timeline_position_ms', sa.Integer, nullable=True),
        sa.Column('status', line_tracking_status_enum, nullable=False, server_default='unassigned'),
        sa.Column('metadata', pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_line_tracking_video_generation_id', 'line_tracking', ['video_generation_id'])
    op.create_index('ix_line_tracking_sequence_unit_id', 'line_tracking', ['sequence_unit_id'])

    # --- Create shot_diversity_reports table ---
    op.create_table(
        'shot_diversity_reports',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_generation_id', pg.UUID(as_uuid=True),
                  sa.ForeignKey('video_generations.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('total_shots', sa.Integer, nullable=False),
        sa.Column('duplicate_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('near_duplicate_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('unique_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('intentional_motif_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('report_data', pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('status', shot_diversity_report_status_enum, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_shot_diversity_reports_video_generation_id', 'shot_diversity_reports', ['video_generation_id'])

    # --- Create continuity_references table ---
    op.create_table(
        'continuity_references',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_generation_id', pg.UUID(as_uuid=True),
                  sa.ForeignKey('video_generations.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('reference_type', continuity_reference_type_enum, nullable=False),
        sa.Column('reference_id', sa.String, nullable=False),
        sa.Column('reference_data', pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('shot_ids', pg.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('adjacent_shot_qa', pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_continuity_references_video_generation_id', 'continuity_references', ['video_generation_id'])


def downgrade() -> None:
    # --- Drop tables ---
    op.drop_index('ix_continuity_references_video_generation_id', table_name='continuity_references')
    op.drop_table('continuity_references')

    op.drop_index('ix_shot_diversity_reports_video_generation_id', table_name='shot_diversity_reports')
    op.drop_table('shot_diversity_reports')

    op.drop_index('ix_line_tracking_sequence_unit_id', table_name='line_tracking')
    op.drop_index('ix_line_tracking_video_generation_id', table_name='line_tracking')
    op.drop_table('line_tracking')

    op.drop_index('ix_sequence_units_video_generation_id', table_name='sequence_units')
    op.drop_table('sequence_units')

    # --- Drop ENUM types ---
    pg.ENUM(name='continuity_reference_type', create_type=False).drop(op.get_bind(), checkfirst=True)
    pg.ENUM(name='shot_diversity_report_status', create_type=False).drop(op.get_bind(), checkfirst=True)
    pg.ENUM(name='line_tracking_status', create_type=False).drop(op.get_bind(), checkfirst=True)
    pg.ENUM(name='sequence_unit_status', create_type=False).drop(op.get_bind(), checkfirst=True)
    pg.ENUM(name='sequence_unit_type', create_type=False).drop(op.get_bind(), checkfirst=True)