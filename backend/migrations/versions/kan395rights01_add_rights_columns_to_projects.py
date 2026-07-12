"""KAN-395: add copyright/rights provenance columns to projects

These columns were added to the Project model in commit b19297a
(feat(kan-395): Copyright capture + classification fields on Project)
but NO Alembic migration was ever created for them. As a result the ORM
emits `SELECT ... projects.original_work_title ...` while the column does
not exist in the DB, producing a 500 on GET /api/v1/projects/.

Revision ID: kan395rights01
Revises: 94457dda5f87
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "kan395rights01"
down_revision: Union[str, Sequence[str], None] = "94457dda5f87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the KAN-395 rights/provenance columns to `projects`.

    All six string columns are nullable (model default None), so they add
    cleanly to a populated table with no backfill. `requires_attribution`
    is NOT NULL in the model (bool default False); a server_default of
    `false` is REQUIRED so the ADD COLUMN succeeds on prod's existing rows.
    """
    op.add_column("projects", sa.Column("original_work_title", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("projects", sa.Column("original_work_author", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("projects", sa.Column("original_work_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("projects", sa.Column("rights_ownership", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("projects", sa.Column("rights_notes", sa.TEXT(), nullable=True))
    op.add_column("projects", sa.Column("content_classification", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column(
        "projects",
        sa.Column(
            "requires_attribution",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Drop the server_default now that every existing row is backfilled to
    # false; the model manages the default in Python going forward. This
    # keeps the DB schema aligned with the model (which has no server_default).
    op.alter_column("projects", "requires_attribution", server_default=None)


def downgrade() -> None:
    """Drop the KAN-395 rights/provenance columns."""
    op.drop_column("projects", "requires_attribution")
    op.drop_column("projects", "content_classification")
    op.drop_column("projects", "rights_notes")
    op.drop_column("projects", "rights_ownership")
    op.drop_column("projects", "original_work_url")
    op.drop_column("projects", "original_work_author")
    op.drop_column("projects", "original_work_title")
