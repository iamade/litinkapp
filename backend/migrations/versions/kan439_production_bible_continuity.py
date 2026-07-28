"""KAN-439: Production bible, voice casting, dialogue manifest

Revision ID: kan439_production_bible
Revises: scriptstandard02
Create Date: 2026-07-21 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "kan439_production_bible"
down_revision: Union[str, Sequence[str], None] = "scriptstandard02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create production_bibles, voice_castings, dialogue_manifests tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ── production_bibles ──
    if not bind.has_table("production_bibles"):
        op.create_table(
            "production_bibles",
            sa.Column(
                "id",
                sa.UUID(),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("project_id", sa.UUID(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "characters",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=True,
            ),
            sa.Column(
                "objects",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=True,
            ),
            sa.Column(
                "locations",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=True,
            ),
            sa.Column(
                "voices",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=True,
            ),
            sa.Column(
                "pronunciation",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=True,
            ),
            sa.Column(
                "style_rules",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=True,
            ),
            sa.Column(
                "world_rules",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=True,
            ),
            sa.Column(
                "approved_reference_assets",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=True,
            ),
            sa.Column("change_log", sa.TEXT(), nullable=True),
            sa.Column("created_by", sa.UUID(), nullable=True),
            sa.Column(
                "created_at",
                postgresql.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                postgresql.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["project_id"], ["projects.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    # Guard indexes for production_bibles
    existing_indexes_pb = {idx["name"] for idx in inspector.get_indexes("production_bibles")} if bind.has_table("production_bibles") else set()
    if "ix_production_bibles_project_id" not in existing_indexes_pb:
        op.create_index(
            op.f("ix_production_bibles_project_id"),
            "production_bibles",
            ["project_id"],
            unique=False,
        )
    if "ix_production_bibles_created_by" not in existing_indexes_pb:
        op.create_index(
            op.f("ix_production_bibles_created_by"),
            "production_bibles",
            ["created_by"],
            unique=False,
        )

    # ── voice_castings ──
    if not bind.has_table("voice_castings"):
        op.create_table(
            "voice_castings",
            sa.Column(
                "id",
                sa.UUID(),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("project_id", sa.UUID(), nullable=False),
            sa.Column("character_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("voice_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column(
                "voice_metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=True,
            ),
            sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column(
                "created_at",
                postgresql.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                postgresql.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["project_id"], ["projects.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "project_id",
                "character_name",
                name="uq_voice_casting_project_character",
            ),
        )

    # Guard indexes for voice_castings
    existing_indexes_vc = {idx["name"] for idx in inspector.get_indexes("voice_castings")} if bind.has_table("voice_castings") else set()
    if "ix_voice_castings_project_id" not in existing_indexes_vc:
        op.create_index(
            op.f("ix_voice_castings_project_id"),
            "voice_castings",
            ["project_id"],
            unique=False,
        )
    if "ix_voice_castings_character_name" not in existing_indexes_vc:
        op.create_index(
            op.f("ix_voice_castings_character_name"),
            "voice_castings",
            ["character_name"],
            unique=False,
        )

    # ── dialogue_manifests ──
    if not bind.has_table("dialogue_manifests"):
        op.create_table(
            "dialogue_manifests",
            sa.Column(
                "id",
                sa.UUID(),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("project_id", sa.UUID(), nullable=False),
            sa.Column("video_generation_id", sa.UUID(), nullable=True),
            sa.Column(
                "content_hash",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
            ),
            sa.Column("scene_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("speaker", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("manifest_text", sa.TEXT(), nullable=False),
            sa.Column("sequence_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("audio_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
            sa.Column("audio_generation_id", sa.UUID(), nullable=True),
            sa.Column("subtitle_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("subtitle_format", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("lip_sync_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("lip_sync_status", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("merge_output_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("merge_status", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("voice_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("voice_provider", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column(
                "scene_state",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=True,
            ),
            sa.Column("previous_frame_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("continuity_frame_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column(
                "status",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column(
                "created_at",
                postgresql.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                postgresql.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["project_id"], ["projects.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["video_generation_id"],
                ["video_generations.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("content_hash", name="uq_dialogue_manifest_content_hash"),
        )

    # Guard indexes for dialogue_manifests
    existing_indexes_dm = {idx["name"] for idx in inspector.get_indexes("dialogue_manifests")} if bind.has_table("dialogue_manifests") else set()
    if "ix_dialogue_manifests_project_id" not in existing_indexes_dm:
        op.create_index(
            op.f("ix_dialogue_manifests_project_id"),
            "dialogue_manifests",
            ["project_id"],
            unique=False,
        )
    if "ix_dialogue_manifests_video_generation_id" not in existing_indexes_dm:
        op.create_index(
            op.f("ix_dialogue_manifests_video_generation_id"),
            "dialogue_manifests",
            ["video_generation_id"],
            unique=False,
        )
    if "ix_dialogue_manifests_content_hash" not in existing_indexes_dm:
        op.create_index(
            op.f("ix_dialogue_manifests_content_hash"),
            "dialogue_manifests",
            ["content_hash"],
            unique=True,
        )
    if "ix_dialogue_manifests_scene_id" not in existing_indexes_dm:
        op.create_index(
            op.f("ix_dialogue_manifests_scene_id"),
            "dialogue_manifests",
            ["scene_id"],
            unique=False,
        )
    if "ix_dialogue_manifests_audio_generation_id" not in existing_indexes_dm:
        op.create_index(
            op.f("ix_dialogue_manifests_audio_generation_id"),
            "dialogue_manifests",
            ["audio_generation_id"],
            unique=False,
        )


def downgrade() -> None:
    """Drop production_bibles, voice_castings, dialogue_manifests tables."""
    bind = op.get_bind()
    if bind.has_table("dialogue_manifests"):
        inspector = sa.inspect(bind)
        for idx_name in [
            "ix_dialogue_manifests_audio_generation_id",
            "ix_dialogue_manifests_scene_id",
            "ix_dialogue_manifests_content_hash",
            "ix_dialogue_manifests_video_generation_id",
            "ix_dialogue_manifests_project_id",
        ]:
            existing = {idx["name"] for idx in inspector.get_indexes("dialogue_manifests")}
            if idx_name in existing:
                op.drop_index(op.f(idx_name), table_name="dialogue_manifests")
        op.drop_table("dialogue_manifests")

    if bind.has_table("voice_castings"):
        inspector = sa.inspect(bind)
        for idx_name in [
            "ix_voice_castings_character_name",
            "ix_voice_castings_project_id",
        ]:
            existing = {idx["name"] for idx in inspector.get_indexes("voice_castings")}
            if idx_name in existing:
                op.drop_index(op.f(idx_name), table_name="voice_castings")
        op.drop_table("voice_castings")

    if bind.has_table("production_bibles"):
        inspector = sa.inspect(bind)
        for idx_name in [
            "ix_production_bibles_created_by",
            "ix_production_bibles_project_id",
        ]:
            existing = {idx["name"] for idx in inspector.get_indexes("production_bibles")}
            if idx_name in existing:
                op.drop_index(op.f(idx_name), table_name="production_bibles")
        op.drop_table("production_bibles")
