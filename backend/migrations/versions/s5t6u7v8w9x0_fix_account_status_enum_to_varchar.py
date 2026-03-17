"""fix_account_status_enum_to_varchar

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-03-17

Root cause:
  The `account_status` column on the "user" table was created with a
  PostgreSQL ENUM type (accountstatusschema) at some point when the DB
  was bootstrapped via create_all() with an older model definition that
  used AccountStatusSchema as the column type.

  The current SQLModel definition (schema.py) specifies String / VARCHAR:
      account_status: str = Field(
          default=AccountStatusSchema.INACTIVE.value,
          sa_column=Column(String, nullable=False, ...),
      )

  This mismatch causes every INSERT during registration to fail with:
      column "account_status" is of type accountstatusschema
      but expression is of type character varying

  This is the same class of bug that was fixed for security_question in
  migration r4s5t6u7v8w9.  The model already uses AccountStatusSchema
  only as a Python/Pydantic enum (for default values and business logic),
  not as a DB-level enum type.

Fix: convert the column to plain VARCHAR and drop the stale ENUM type.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "s5t6u7v8w9x0"
down_revision: Union[str, Sequence[str], None] = "r4s5t6u7v8w9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast current ENUM values to text, then to varchar.
    # Using USING clause handles the type coercion safely.
    op.execute(
        "ALTER TABLE \"user\" ALTER COLUMN account_status "
        "TYPE VARCHAR USING account_status::text"
    )
    # Drop the now-unused ENUM type if it still exists.
    op.execute("DROP TYPE IF EXISTS accountstatusschema")


def downgrade() -> None:
    # Recreate the enum and convert the column back (best-effort).
    op.execute(
        "CREATE TYPE accountstatusschema AS ENUM "
        "('active', 'inactive', 'locked', 'pending')"
    )
    op.execute(
        "ALTER TABLE \"user\" ALTER COLUMN account_status "
        "TYPE accountstatusschema USING account_status::accountstatusschema"
    )
