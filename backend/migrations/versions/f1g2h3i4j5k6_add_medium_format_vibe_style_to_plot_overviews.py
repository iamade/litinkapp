"""add_medium_format_vibe_style_to_plot_overviews

Revision ID: f1g2h3i4j5k6
Revises: b12162069bf2
Create Date: 2026-01-11 03:21:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "f1g2h3i4j5k6"
down_revision: Union[str, Sequence[str], None] = "b12162069bf2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add medium field (Animation, Live Action, Hybrid, Puppetry, Stop-Motion)
    op.add_column(
        "plot_overviews",
        sa.Column("medium", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )

    # Add format field (Film, TV Series, Limited Series, Short Film, etc.)
    op.add_column(
        "plot_overviews",
        sa.Column("format", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )

    # Add vibe_style field (Satire, Cinematic, Sitcom, etc.)
    op.add_column(
        "plot_overviews",
        sa.Column("vibe_style", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("plot_overviews", "vibe_style")
    op.drop_column("plot_overviews", "format")
    op.drop_column("plot_overviews", "medium")
