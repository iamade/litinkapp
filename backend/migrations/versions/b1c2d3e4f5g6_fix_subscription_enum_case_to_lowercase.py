"""fix_subscription_enum_case_to_lowercase

Revision ID: b1c2d3e4f5g6
Revises: a4b5c6d7e8f9
Create Date: 2026-04-23

Normalizes subscription_tier and subscription_status PG enums to lowercase.
These enums had duplicate uppercase and lowercase values due to initial
creation using Python enum names (uppercase) and later ALTER TYPE ADD VALUE
for lowercase equivalents.

This migration:
1. Converts columns to text temporarily
2. Updates any remaining uppercase values to lowercase
3. Drops and recreates enum types with lowercase-only values
4. Converts columns back to the new enum types
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5g6"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None

# Enum mappings: (enum_name, table, column, [(OLD_uppercase, new_lowercase), ...])
# Only uppercase→lowercase mappings needed; already-lowercase values are left as-is.
ENUM_FIXES = [
    (
        "subscription_tier",
        "user_subscriptions",
        "tier",
        [
            ("FREE", "free"),
            ("BASIC", "basic"),
            ("PRO", "pro"),
            # lowercase values already exist in PG enum but won't appear in data
            # after migration: premium, professional, enterprise (already lowercase)
        ],
    ),
    (
        "subscription_status",
        "user_subscriptions",
        "status",
        [
            ("ACTIVE", "active"),
            ("CANCELLED", "cancelled"),
            ("EXPIRED", "expired"),
            ("PAST_DUE", "past_due"),
            ("TRIALING", "trialing"),
        ],
    ),
]

# Complete set of lowercase values for each enum
SUBSCRIPTION_TIER_VALUES = ["free", "basic", "pro", "premium", "professional", "enterprise"]
SUBSCRIPTION_STATUS_VALUES = ["active", "cancelled", "expired", "past_due", "trialing"]


def upgrade() -> None:
    for enum_name, table, column, mappings in ENUM_FIXES:
        # Step 1: Change column to text temporarily
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE text USING {column}::text"
        )

        # Step 2: Update existing uppercase values to lowercase
        for old_val, new_val in mappings:
            op.execute(
                f"UPDATE {table} SET {column} = '{new_val}' WHERE {column} = '{old_val}'"
            )

        # Step 3: Drop the old enum type (has mixed-case duplicates)
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    # Step 4: Create the new enums with lowercase-only values
    tier_values = ", ".join(f"'{v}'" for v in SUBSCRIPTION_TIER_VALUES)
    op.execute(f"CREATE TYPE subscription_tier AS ENUM ({tier_values})")

    status_values = ", ".join(f"'{v}'" for v in SUBSCRIPTION_STATUS_VALUES)
    op.execute(f"CREATE TYPE subscription_status AS ENUM ({status_values})")

    # Step 5: Change columns back to the enum types
    op.execute(
        "ALTER TABLE user_subscriptions ALTER COLUMN tier TYPE subscription_tier "
        "USING tier::subscription_tier"
    )
    op.execute(
        "ALTER TABLE user_subscriptions ALTER COLUMN status TYPE subscription_status "
        "USING status::subscription_status"
    )


def downgrade() -> None:
    # Convert back to text
    op.execute(
        "ALTER TABLE user_subscriptions ALTER COLUMN tier TYPE text USING tier::text"
    )
    op.execute(
        "ALTER TABLE user_subscriptions ALTER COLUMN status TYPE text USING status::text"
    )

    # Update lowercase back to uppercase
    for enum_name, table, column, mappings in ENUM_FIXES:
        for old_val, new_val in mappings:
            op.execute(
                f"UPDATE {table} SET {column} = '{old_val}' WHERE {column} = '{new_val}'"
            )

    # Drop lowercase enums
    op.execute("DROP TYPE IF EXISTS subscription_tier")
    op.execute("DROP TYPE IF EXISTS subscription_status")

    # Recreate with uppercase values (original state)
    op.execute(
        "CREATE TYPE subscription_tier AS ENUM ('FREE', 'BASIC', 'PRO', 'premium', 'professional', 'enterprise')"
    )
    op.execute(
        "CREATE TYPE subscription_status AS ENUM ('ACTIVE', 'CANCELLED', 'EXPIRED', 'PAST_DUE', 'TRIALING')"
    )

    # Convert columns back
    op.execute(
        "ALTER TABLE user_subscriptions ALTER COLUMN tier TYPE subscription_tier "
        "USING tier::subscription_tier"
    )
    op.execute(
        "ALTER TABLE user_subscriptions ALTER COLUMN status TYPE subscription_status "
        "USING status::subscription_status"
    )