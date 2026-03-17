"""fix_security_question_enum_to_varchar

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-03-17

The security_question column was left as a PostgreSQL ENUM type
(securityquestionsschema) but the SQLModel definition uses String(30).
This mismatch causes registration to fail with:
  column "security_question" is of type securityquestionsschema
  but expression is of type character varying

Fix: convert the column to VARCHAR(30) and drop the stale ENUM type.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r4s5t6u7v8w9"
down_revision: Union[str, Sequence[str], None] = "q3r4s5t6u7v8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast current ENUM values to text, then to varchar(30).
    # Using USING clause handles the type coercion safely.
    op.execute(
        "ALTER TABLE \"user\" ALTER COLUMN security_question "
        "TYPE VARCHAR(30) USING security_question::text"
    )
    # Drop the now-unused ENUM type if it still exists.
    op.execute("DROP TYPE IF EXISTS securityquestionsschema")


def downgrade() -> None:
    # Recreate the enum and convert the column back (best-effort).
    op.execute(
        "CREATE TYPE securityquestionsschema AS ENUM "
        "('mother_maiden_name', 'childhood_friend', 'favorite_color', 'birth_city')"
    )
    op.execute(
        "ALTER TABLE \"user\" ALTER COLUMN security_question "
        "TYPE securityquestionsschema USING security_question::securityquestionsschema"
    )
