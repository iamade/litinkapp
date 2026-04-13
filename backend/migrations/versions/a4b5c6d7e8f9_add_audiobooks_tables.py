"""add audiobooks and audiobook_chapters tables

Revision ID: a4b5c6d7e8f9
Revises: z3b4c5d6e7f8
Create Date: 2026-04-11

Adds audiobooks and audiobook_chapters tables for the
audiobook generation service (KAN-176).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "z3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audiobooks table
    op.create_table(
        "audiobooks",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "book_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("voice_id", sa.String, nullable=True),
        sa.Column("total_chapters", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "completed_chapters", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "total_duration_seconds", sa.Float, nullable=True, server_default="0.0"
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("credits_reserved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("credits_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Create audiobook_chapters table
    op.create_table(
        "audiobook_chapters",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "audiobook_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("audiobooks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "chapter_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("chapter_number", sa.Integer, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("audio_url", sa.String, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True, server_default="0.0"),
        sa.Column("credits_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("audiobook_chapters")
    op.drop_table("audiobooks")
