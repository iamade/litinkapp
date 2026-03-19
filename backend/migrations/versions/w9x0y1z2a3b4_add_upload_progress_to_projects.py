"""add upload progress columns to projects table

Revision ID: w9x0y1z2a3b4
Revises: v8w9x0y1z2a3
Create Date: 2026-03-19

Adds upload_status, upload_progress, upload_stage, upload_error,
upload_total_chapters, upload_chapters_processed columns to the
projects table so the frontend can poll live progress during
background upload processing (KAN-102).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "w9x0y1z2a3b4"
down_revision: Union[str, Sequence[str], None] = "v8w9x0y1z2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE projects
            ADD COLUMN IF NOT EXISTS upload_status         VARCHAR,
            ADD COLUMN IF NOT EXISTS upload_progress       INTEGER,
            ADD COLUMN IF NOT EXISTS upload_stage          VARCHAR,
            ADD COLUMN IF NOT EXISTS upload_error          TEXT,
            ADD COLUMN IF NOT EXISTS upload_total_chapters INTEGER,
            ADD COLUMN IF NOT EXISTS upload_chapters_processed INTEGER;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE projects
            DROP COLUMN IF EXISTS upload_status,
            DROP COLUMN IF EXISTS upload_progress,
            DROP COLUMN IF EXISTS upload_stage,
            DROP COLUMN IF EXISTS upload_error,
            DROP COLUMN IF EXISTS upload_total_chapters,
            DROP COLUMN IF EXISTS upload_chapters_processed;
        """
    )
