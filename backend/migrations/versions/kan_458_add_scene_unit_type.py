"""KAN-458: add 'scene' to sequence_unit_type enum

PSQ 13-route probe on ``origin/dev_branch @ 86a27d6`` identified KAN-458:
DB enum ``sequence_unit_type`` declares 6 values
(ident_title, prologue, dialogue_act, climax_resolution, closing_bookend,
end_title_credits) but PSQ test harness POSTs with
``unit_type="scene"`` — DB rejects with
``asyncpg.exceptions.InvalidTextRepresentationError: invalid input value
for enum sequence_unit_type: "scene"``.

LC dispatch (msg ``1534174532619730984``, 12:21:52 UTC): add 'scene' to
DB enum; request schema is authoritative for client-facing values.

Fix: ``ALTER TYPE sequence_unit_type ADD VALUE 'scene'`` (Postgres-specific
DDL). ORM ``SequenceUnitType`` enum gains ``SCENE = "scene"``. Service
``REQUIRED_UNIT_TYPES`` list gains ``"scene"``.

Diff:
- ``backend/app/videos/models.py`` — add ``SCENE`` enum member
- ``backend/app/core/services/cinematic_episode_gate_service.py`` — add
  ``"scene"`` to ``REQUIRED_UNIT_TYPES``
- ``backend/app/api/routes/ai/cinematic_gates.py`` — update field
  description on ``SequenceUnitCreate.unit_type``
- ``backend/migrations/versions/kan_458_add_scene_unit_type.py`` — this file

Revision ID: kan_458_add_scene_unit_type
Revises: kan_438_video_segments_sequence_index
Create Date: 2026-08-04 13:15:00.000000
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'kan_458_add_scene_unit_type'
down_revision = 'kan_438_video_segments_sequence_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add 'scene' to sequence_unit_type PG enum."""
    # Postgres ALTER TYPE ... ADD VALUE cannot run inside a transaction block
    # in older PG versions, but PG 12+ supports it. We're on PG 15, so this
    # is fine. If it ever fails, set autocommit=True on op.get_bind().
    op.execute("ALTER TYPE sequence_unit_type ADD VALUE IF NOT EXISTS 'scene'")


def downgrade() -> None:
    """Remove 'scene' from sequence_unit_type PG enum.

    NOTE: Postgres cannot drop a single enum value in place — the only way
    to remove a value is to recreate the type. We leave the 'scene' value
    in place on downgrade to preserve data integrity. A separate ticket
    should rename or remove it if needed.
    """
    # Intentionally a no-op: see note above.
    pass