"""KAN-438 regression fix: add sequence_index column to video_segments

The cinematic-gates runtime services (shot_diversity_service.py:72 and
continuity_service.py:177) reference ``video_segments.sequence_index`` for
``ORDER BY`` and ``adjacent_shot_qa`` payload keys. The original KAN-438
migration ``kan438_cinematic_dialogue_episode_gates`` added four new tables
(sequence_units, line_tracking, shot_diversity_reports, continuity_references)
but never propagated ``sequence_index`` onto the existing ``video_segments``
table or onto the ``VideoSegment`` SQLModel. The result is a runtime crash
on every ``POST /api/v1/ai/cinematic-gates/{vg_id}/shot-diversity/analyze``
call plus the ``adjacent_shot_qa`` sub-flow on continuity_references.

Fix: add ``sequence_index int`` to ``video_segments`` matching the ORM
intent. Backend writes are populated via ``scene_number`` (the existing
ordering field) by ``video_tasks.py`` insert paths. Existing rows are
backfilled in-place.

Revision ID: kan_438_video_segments_sequence_index
Revises: merge_kan438_439
Create Date: 2026-08-04 06:45:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'kan_438_video_segments_sequence_index'
down_revision = 'merge_kan438_439'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ``sequence_index`` int column + backfill from scene_number + index it."""
    bind = op.get_bind()

    # 1. Create the column nullable first so existing rows migrate cleanly.
    op.add_column(
        'video_segments',
        sa.Column(
            'sequence_index',
            sa.Integer(),
            nullable=True,
        ),
    )

    # 2. Backfill existing rows using scene_number so ORDER BY returns a
    #    meaningful sequence. New rows are populated by the inserts in
    #    video_tasks.py and lipsync_tasks.py (forward fix in those files).
    bind.execute(
        sa.text(
            "UPDATE video_segments "
            "SET sequence_index = scene_number "
            "WHERE sequence_index IS NULL"
        )
    )

    # 3. Add the ``NOT NULL`` constraint + an index on
    #    (video_generation_id, sequence_index) which is the access pattern
    #    of the two cinematic-gates reads.
    op.alter_column(
        'video_segments',
        'sequence_index',
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_index(
        'ix_video_segments_video_generation_id_sequence_index',
        'video_segments',
        ['video_generation_id', 'sequence_index'],
        unique=False,
    )


def downgrade() -> None:
    """Reverse: drop the index + column."""
    op.drop_index(
        'ix_video_segments_video_generation_id_sequence_index',
        table_name='video_segments',
    )
    op.drop_column('video_segments', 'sequence_index')
