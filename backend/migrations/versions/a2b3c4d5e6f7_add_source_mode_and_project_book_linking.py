"""add source_mode and project_book_linking

Revision ID: a2b3c4d5e6f7
Revises: fae90d574863
Create Date: 2026-01-07 12:40:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "a2b3c4d5e6f7"
down_revision = "717fed1bf007"
branch_labels = None
depends_on = None


def upgrade():
    # Add source_mode column to books table (default "explorer" for existing books)
    op.add_column(
        "books",
        sa.Column(
            "source_mode", sa.String(), nullable=False, server_default="explorer"
        ),
    )

    # Add project_id column to books table (foreign key to projects)
    op.add_column(
        "books", sa.Column("project_id", pg.UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_books_project_id", "books", ["project_id"], unique=False)
    op.create_foreign_key(
        "fk_books_project_id",
        "books",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add book_id column to projects table (foreign key to books)
    op.add_column(
        "projects", sa.Column("book_id", pg.UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_projects_book_id", "projects", ["book_id"], unique=False)
    op.create_foreign_key(
        "fk_projects_book_id",
        "projects",
        "books",
        ["book_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    # Remove book_id from projects
    op.drop_constraint("fk_projects_book_id", "projects", type_="foreignkey")
    op.drop_index("ix_projects_book_id", table_name="projects")
    op.drop_column("projects", "book_id")

    # Remove project_id from books
    op.drop_constraint("fk_books_project_id", "books", type_="foreignkey")
    op.drop_index("ix_books_project_id", table_name="books")
    op.drop_column("books", "project_id")

    # Remove source_mode from books
    op.drop_column("books", "source_mode")
