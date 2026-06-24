"""Backfill artifact content_type from chapters

Revision ID: 94457dda5f87
Revises: k367v3a1b2c3
Create Date: 2026-06-21 07:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import engine_from_config
from sqlalchemy.engine import reflection
import sqlalchemy as sa
import logging

# revision identifiers, used by Alembic.
revision: str = '94457dda5f87'
down_revision: Union[str, Sequence[str], None] = 'k367v3a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    return table_name in insp.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    if table_name not in insp.get_table_names():
        return False
    cols = {c['name'] for c in insp.get_columns(table_name)}
    return column_name in cols


def _column_type(table_name: str, column_name: str) -> str:
    """Return a lower-cased string representation of the column type."""
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    for c in insp.get_columns(table_name):
        if c['name'] == column_name:
            return str(c['type']).lower()
    return ''


def upgrade() -> None:
    """Backfill artifacts.content->>'content_type' from linked chapters.content_type."""
    # Defensive pre-checks: if any required table/column/type is missing, skip the
    # backfill. Production may be in a partial/legacy state where one of these
    # prerequisites is absent.
    if not _table_exists('artifacts'):
        logger.warning("Migration 94457dda5f87: artifacts table does not exist; skipping backfill.")
        return
    if not _table_exists('chapters'):
        logger.warning("Migration 94457dda5f87: chapters table does not exist; skipping backfill.")
        return
    if not _has_column('artifacts', 'content'):
        logger.warning("Migration 94457dda5f87: artifacts.content column does not exist; skipping backfill.")
        return
    if not _has_column('artifacts', 'artifact_type'):
        logger.warning("Migration 94457dda5f87: artifacts.artifact_type column does not exist; skipping backfill.")
        return
    if not _has_column('chapters', 'content_type'):
        logger.warning("Migration 94457dda5f87: chapters.content_type column does not exist; skipping backfill.")
        return

    content_type = _column_type('artifacts', 'content')
    if 'jsonb' not in content_type and 'json' not in content_type:
        logger.warning(
            "Migration 94457dda5f87: artifacts.content is not JSONB/JSON (found %s); skipping backfill.",
            content_type,
        )
        return

    # The update is guarded by jsonb_typeof(content) = 'object' so jsonb_set does
    # not fail on scalar/null JSON values. artifact_type comparison uses ::text to
    # tolerate enum vs text differences. chapter_id is compared as text to avoid
    # UUID/enum issues. content_type is cast to text before to_jsonb to ensure a
    # valid JSON string value even if chapters.content_type is an enum.
    op.execute(
        """
        UPDATE artifacts AS a
        SET content = jsonb_set(a.content, '{content_type}', to_jsonb(c.content_type::text))
        FROM chapters AS c
        WHERE a.artifact_type::text = 'CHAPTER'
          AND jsonb_typeof(a.content) = 'object'
          AND a.content->>'chapter_id' IS NOT NULL
          AND a.content->>'chapter_id' = c.id::text
          AND a.content->>'content_type' IS NULL;
        """
    )


def downgrade() -> None:
    """Remove content_type key from artifact content where it was backfilled."""
    if not _table_exists('artifacts'):
        logger.warning("Migration 94457dda5f87 downgrade: artifacts table does not exist; skipping.")
        return
    if not _has_column('artifacts', 'content'):
        logger.warning("Migration 94457dda5f87 downgrade: artifacts.content column does not exist; skipping.")
        return
    if not _has_column('artifacts', 'artifact_type'):
        logger.warning("Migration 94457dda5f87 downgrade: artifacts.artifact_type column does not exist; skipping.")
        return

    content_type = _column_type('artifacts', 'content')
    if 'jsonb' not in content_type and 'json' not in content_type:
        logger.warning(
            "Migration 94457dda5f87 downgrade: artifacts.content is not JSONB/JSON (found %s); skipping.",
            content_type,
        )
        return

    op.execute(
        """
        UPDATE artifacts AS a
        SET content = a.content - 'content_type'
        WHERE a.artifact_type::text = 'CHAPTER'
          AND jsonb_typeof(a.content) = 'object'
          AND a.content->>'chapter_id' IS NOT NULL
          AND a.content->>'content_type' IS NOT NULL;
        """
    )
