"""fix chapter enum case to uppercase

Revision ID: o1p2q3r4s5t6
Revises: n0p1q2r3s4t5
Create Date: 2026-03-04

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o1p2q3r4s5t6"
down_revision: Union[str, Sequence[str], None] = "n0p1q2r3s4t5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix artifact_type enum: ensure CHAPTER exists in uppercase."""
    # Supabase doesn't allow direct pg_enum modification, so we need to
    # recreate the enum type with proper values.

    # Step 1: Change column to text temporarily
    op.execute(
        "ALTER TABLE artifacts ALTER COLUMN artifact_type TYPE text USING artifact_type::text"
    )

    # Step 2: Normalize any lowercase 'chapter' values to uppercase 'CHAPTER'
    op.execute(
        "UPDATE artifacts SET artifact_type = 'CHAPTER' WHERE artifact_type = 'chapter'"
    )

    # Step 3: Drop the old enum type
    op.execute("DROP TYPE IF EXISTS artifact_type")

    # Step 4: Create the new enum with all correct uppercase values (including CHAPTER)
    op.execute(
        "CREATE TYPE artifact_type AS ENUM ("
        "'PLOT', 'SCRIPT', 'STORYBOARD', 'IMAGE', 'AUDIO', 'VIDEO', "
        "'CHAPTER', 'DOCUMENT_SUMMARY'"
        ")"
    )

    # Step 5: Change column back to the enum type
    op.execute(
        "ALTER TABLE artifacts ALTER COLUMN artifact_type TYPE artifact_type USING artifact_type::artifact_type"
    )


def downgrade() -> None:
    """Downgrade - revert to enum without CHAPTER (original state)."""
    op.execute(
        "ALTER TABLE artifacts ALTER COLUMN artifact_type TYPE text USING artifact_type::text"
    )
    op.execute("DELETE FROM artifacts WHERE artifact_type = 'CHAPTER'")
    op.execute("DROP TYPE IF EXISTS artifact_type")
    op.execute(
        "CREATE TYPE artifact_type AS ENUM ("
        "'PLOT', 'SCRIPT', 'STORYBOARD', 'IMAGE', 'AUDIO', 'VIDEO', "
        "'DOCUMENT_SUMMARY'"
        ")"
    )
    op.execute(
        "ALTER TABLE artifacts ALTER COLUMN artifact_type TYPE artifact_type USING artifact_type::artifact_type"
    )
