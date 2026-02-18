"""fix enum case to lowercase

Revision ID: l8m9n0p1q2r3
Revises: k7l8m9n0p1q2
Create Date: 2026-02-09 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l8m9n0p1q2r3"
down_revision: Union[str, Sequence[str], None] = "k7l8m9n0p1q2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum mappings: (enum_name, table, column, [(OLD, new), ...])
ENUM_FIXES = [
    (
        "video_generation_status",
        "video_generations",
        "generation_status",
        [
            ("PENDING", "pending"),
            ("GENERATING_AUDIO", "generating_audio"),
            ("AUDIO_COMPLETED", "audio_completed"),
            ("GENERATING_IMAGES", "generating_images"),
            ("IMAGES_COMPLETED", "images_completed"),
            ("GENERATING_VIDEO", "generating_video"),
            ("VIDEO_COMPLETED", "video_completed"),
            ("MERGING_AUDIO", "merging_audio"),
            ("APPLYING_LIPSYNC", "applying_lipsync"),
            ("COMBINING", "combining"),
            ("COMPLETED", "completed"),
            ("FAILED", "failed"),
            ("RETRYING", "retrying"),
        ],
    ),
    (
        "video_quality_tier",
        "video_generations",
        "quality_tier",
        [
            ("FREE", "free"),
            ("BASIC", "basic"),
            ("STANDARD", "standard"),
            ("STANDARD_2", "standard_2"),
            ("PRO", "pro"),
            ("MASTER", "master"),
        ],
    ),
    (
        "audio_type",
        "audio_generations",
        "audio_type",
        [
            ("NARRATOR", "narrator"),
            ("CHARACTER", "character"),
            ("SOUND_EFFECTS", "sound_effects"),
            ("BACKGROUND_MUSIC", "background_music"),
        ],
    ),
]


def upgrade() -> None:
    for enum_name, table, column, mappings in ENUM_FIXES:
        # Step 1: Change column to text temporarily
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE text USING {column}::text"
        )

        # Step 2: Update existing uppercase values to lowercase
        for old_val, new_val in mappings:
            op.execute(
                f"UPDATE {table} SET {column} = '{new_val}' WHERE {column} = '{old_val}'"
            )

        # Step 3: Drop the old enum type
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

        # Step 4: Create the new enum with lowercase values
        new_values = ", ".join(f"'{new_val}'" for _, new_val in mappings)
        op.execute(f"CREATE TYPE {enum_name} AS ENUM ({new_values})")

        # Step 5: Change column back to the enum type
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {enum_name} USING {column}::{enum_name}"
        )


def downgrade() -> None:
    for enum_name, table, column, mappings in ENUM_FIXES:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE text USING {column}::text"
        )
        for old_val, new_val in mappings:
            op.execute(
                f"UPDATE {table} SET {column} = '{old_val}' WHERE {column} = '{new_val}'"
            )
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
        old_values = ", ".join(f"'{old_val}'" for old_val, _ in mappings)
        op.execute(f"CREATE TYPE {enum_name} AS ENUM ({old_values})")
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {enum_name} USING {column}::{enum_name}"
        )
