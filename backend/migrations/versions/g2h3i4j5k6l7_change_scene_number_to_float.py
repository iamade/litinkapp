"""Change scene_number from INTEGER to DOUBLE PRECISION for sub-scene support

Revision ID: g2h3i4j5k6l7
Revises: f1g2h3i4j5k6
Create Date: 2026-01-15 00:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g2h3i4j5k6l7"
down_revision: Union[str, None] = "e0bc180d1fa9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change scene_number columns from INTEGER to DOUBLE PRECISION to support sub-scenes (1.1, 1.2, etc.)"""

    # Update image_generations table
    op.alter_column(
        "image_generations",
        "scene_number",
        existing_type=sa.INTEGER(),
        type_=sa.Float(),
        existing_nullable=True,
    )

    # Update image_records table (if it exists and has scene_number)
    try:
        op.alter_column(
            "image_records",
            "scene_number",
            existing_type=sa.INTEGER(),
            type_=sa.Float(),
            existing_nullable=True,
        )
    except Exception:
        # Table might not have this column
        pass

    # Update video_segments table (if it has scene_number)
    try:
        op.alter_column(
            "video_segments",
            "scene_number",
            existing_type=sa.INTEGER(),
            type_=sa.Float(),
            existing_nullable=False,
        )
    except Exception:
        # Table might not have this column or it might be nullable
        pass


def downgrade() -> None:
    """Revert scene_number columns back to INTEGER"""

    # Revert image_generations table
    op.alter_column(
        "image_generations",
        "scene_number",
        existing_type=sa.Float(),
        type_=sa.INTEGER(),
        existing_nullable=True,
    )

    # Revert image_records table
    try:
        op.alter_column(
            "image_records",
            "scene_number",
            existing_type=sa.Float(),
            type_=sa.INTEGER(),
            existing_nullable=True,
        )
    except Exception:
        pass

    # Revert video_segments table
    try:
        op.alter_column(
            "video_segments",
            "scene_number",
            existing_type=sa.Float(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )
    except Exception:
        pass
