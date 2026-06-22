"""Backfill artifact content_type from chapters

Revision ID: 94457dda5f87
Revises: k367v3a1b2c3
Create Date: 2026-06-21 07:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '94457dda5f87'
down_revision: Union[str, Sequence[str], None] = 'k367v3a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill artifacts.content->>'content_type' from linked chapters.content_type."""
    # JSONB update via raw SQL: join artifacts.content->>'chapter_id' to chapters.id
    op.execute(
        """
        UPDATE artifacts a
        SET content = jsonb_set(
            content,
            '{content_type}',
            to_jsonb(c.content_type)
        )
        FROM chapters c
        WHERE a.artifact_type = 'CHAPTER'
          AND a.content->>'chapter_id' IS NOT NULL
          AND a.content->>'chapter_id' = c.id::text
          AND a.content->>'content_type' IS NULL;
        """
    )


def downgrade() -> None:
    """Remove content_type key from artifact content where it was backfilled."""
    op.execute(
        """
        UPDATE artifacts
        SET content = content - 'content_type'
        WHERE artifact_type = 'CHAPTER'
          AND content->>'chapter_id' IS NOT NULL
          AND content->>'content_type' IS NOT NULL;
        """
    )
