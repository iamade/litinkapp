"""add updated_at and model_id to image_generations

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-03-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "p2q3r4s5t6u7"
down_revision: Union[str, Sequence[str], None] = "o1p2q3r4s5t6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing updated_at and model_id columns to image_generations (if they don't exist)."""
    # Use raw SQL with IF NOT EXISTS to be safe for both local and production
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'image_generations' AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE image_generations
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'image_generations' AND column_name = 'model_id'
            ) THEN
                ALTER TABLE image_generations
                ADD COLUMN model_id VARCHAR;
            END IF;
        END$$;
    """
    )


def downgrade() -> None:
    """Remove updated_at and model_id columns from image_generations."""
    op.drop_column("image_generations", "model_id")
    op.drop_column("image_generations", "updated_at")
