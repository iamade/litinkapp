"""add activation_token_hash + activation_token_expires_at to user

Revision ID: d1e2f3g4h5i6
Revises: c1d2e3f4g5h6
Create Date: 2026-06-09

Restores the migration that was lost in commit 849e16e
("feat(auth): token-based email activation with Argon2 hashing", 2026-04-12).

That commit ADDED `activation_token_hash` (VARCHAR 128, indexed) and
`activation_token_expires_at` (TIMESTAMPTZ) to the User SQLModel and
simultaneously deleted the original migration
`a4b5c6d7e8f9_add_activation_token_hash_fields.py` because that revision id
collided with `a4b5c6d7e8f9_add_audiobooks_tables.py`. No replacement
migration was generated, so the model has columns the DB schema does not,
which causes a 500 on registration:

  asyncpg.UndefinedColumnError: column user.activation_token_hash does not exist

This migration re-creates both columns and the lookup index. Uses
`IF NOT EXISTS` guards so it is idempotent and safe to apply on any
environment (Mac dev, vps-dev, vps-staging) that may already have the
columns from an earlier hot-patch.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d1e2f3g4h5i6"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4g5h6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE "user"
        ADD COLUMN IF NOT EXISTS activation_token_hash VARCHAR(128),
        ADD COLUMN IF NOT EXISTS activation_token_expires_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_activation_token_hash
        ON "user" (activation_token_hash)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_activation_token_hash")
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS activation_token_expires_at')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS activation_token_hash')
