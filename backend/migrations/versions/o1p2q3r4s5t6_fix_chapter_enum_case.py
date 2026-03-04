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
    """Fix 'chapter' enum value to uppercase 'CHAPTER' to match other enum values."""
    # The previous migration (a1b2c3d4e5f6) added lowercase 'chapter',
    # but all other artifact_type values are UPPERCASE. PostgreSQL enums
    # are case-sensitive, so 'chapter' != 'CHAPTER'.
    op.execute(
        """
        DO $$
        BEGIN
            -- Rename lowercase 'chapter' to uppercase 'CHAPTER' if it exists
            IF EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'chapter' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'artifact_type')
            ) THEN
                UPDATE pg_enum SET enumlabel = 'CHAPTER' 
                WHERE enumlabel = 'chapter' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'artifact_type');
            END IF;

            -- If 'CHAPTER' doesn't exist at all (neither lowercase nor uppercase was added), add it
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'CHAPTER' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'artifact_type')
            ) THEN
                -- We can't use ALTER TYPE ADD VALUE inside a transaction block with DO,
                -- so we'll handle this case separately
                NULL;
            END IF;
        END$$;
    """
    )
    # This handles the case where CHAPTER doesn't exist at all
    op.execute("ALTER TYPE artifact_type ADD VALUE IF NOT EXISTS 'CHAPTER'")


def downgrade() -> None:
    """Downgrade - revert CHAPTER back to lowercase chapter."""
    op.execute(
        """
        UPDATE pg_enum SET enumlabel = 'chapter' 
        WHERE enumlabel = 'CHAPTER' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'artifact_type');
    """
    )
