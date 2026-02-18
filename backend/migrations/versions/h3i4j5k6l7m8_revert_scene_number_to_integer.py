"""Revert scene_number from FLOAT back to INTEGER

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2026-01-15 01:48:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h3i4j5k6l7m8"
down_revision: Union[str, None] = "g2h3i4j5k6l7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Revert scene_number columns from FLOAT back to INTEGER.

    This undoes the previous migration that changed scene_number to FLOAT.
    Integer scene numbers are cleaner and avoid JavaScript float comparison issues
    (e.g., 1.10 === 1.1 in JavaScript).
    """

    # Revert image_generations table
    op.alter_column(
        "image_generations",
        "scene_number",
        existing_type=sa.Float(),
        type_=sa.INTEGER(),
        existing_nullable=True,
        postgresql_using="scene_number::integer",
    )

    # Revert image_records table (if it exists and has scene_number)
    try:
        op.alter_column(
            "image_records",
            "scene_number",
            existing_type=sa.Float(),
            type_=sa.INTEGER(),
            existing_nullable=True,
            postgresql_using="scene_number::integer",
        )
    except Exception:
        # Table might not have this column
        pass

    # Revert video_segments table (if it has scene_number)
    try:
        op.alter_column(
            "video_segments",
            "scene_number",
            existing_type=sa.Float(),
            type_=sa.INTEGER(),
            existing_nullable=False,
            postgresql_using="scene_number::integer",
        )
    except Exception:
        # Table might not have this column
        pass


def downgrade() -> None:
    """Re-apply FLOAT type if needed (reverse of this migration)"""

    # Re-apply FLOAT to image_generations table
    op.alter_column(
        "image_generations",
        "scene_number",
        existing_type=sa.INTEGER(),
        type_=sa.Float(),
        existing_nullable=True,
    )

    # Re-apply FLOAT to image_records table
    try:
        op.alter_column(
            "image_records",
            "scene_number",
            existing_type=sa.INTEGER(),
            type_=sa.Float(),
            existing_nullable=True,
        )
    except Exception:
        pass

    # Re-apply FLOAT to video_segments table
    try:
        op.alter_column(
            "video_segments",
            "scene_number",
            existing_type=sa.INTEGER(),
            type_=sa.Float(),
            existing_nullable=False,
        )
    except Exception:
        pass
