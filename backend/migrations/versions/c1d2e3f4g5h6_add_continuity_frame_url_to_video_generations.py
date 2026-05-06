"""add continuity_frame_url to video_generations

Revision ID: c1d2e3f4g5h6
Revises: b1c2d3e4f5g6
Create Date: 2026-05-06

Adds the persisted continuity-frame URL used by KAN-263 provider-frame
persistence/retest paths.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5g6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "video_generations",
        sa.Column("continuity_frame_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_generations", "continuity_frame_url")
