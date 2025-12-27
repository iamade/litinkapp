"""
Admin User Seeder

Automatically creates default admin and superadmin users at application startup
if they don't already exist in the database.
"""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.auth.schema import (
    RoleChoicesSchema,
    SecurityQuestionsSchema,
    AccountStatusSchema,
)
from app.auth.utils import generate_password_hash, generate_display_name
from app.core.database import async_session
from app.core.logging import get_logger

logger = get_logger()


# Default admin accounts to create at startup
# WARNING: Change these passwords in production!
ADMIN_ACCOUNTS = [
    {
        "email": "support@litinkai.com",
        "password": "password123",
        "first_name": "Super",
        "last_name": "Admin",
        "roles": [
            RoleChoicesSchema.SUPER_ADMIN,
            RoleChoicesSchema.CREATOR,
            RoleChoicesSchema.EXPLORER,
        ],
        "is_active": True,
        "is_superuser": True,
        "security_question": SecurityQuestionsSchema.MOTHER_MAIDEN_NAME,
        "security_answer": "admin",
        "account_status": AccountStatusSchema.ACTIVE,
    },
    {
        "email": "admin@litinkai.com",
        "password": "password123",
        "first_name": "Platform",
        "last_name": "Admin",
        "roles": [
            RoleChoicesSchema.ADMIN,
            RoleChoicesSchema.CREATOR,
            RoleChoicesSchema.EXPLORER,
        ],
        "is_active": True,
        "is_superuser": False,
        "security_question": SecurityQuestionsSchema.FAVORITE_COLOUR,
        "security_answer": "blue",
        "account_status": AccountStatusSchema.ACTIVE,
    },
]


async def seed_admin_users() -> None:
    """
    Create default admin users if they don't exist.

    This function is called during application startup to ensure
    admin accounts are available for initial platform access.
    """
    logger.info("🌱 Checking default admin users...")

    session = async_session()
    try:
        created_count = 0
        skipped_count = 0

        for account in ADMIN_ACCOUNTS:
            try:
                # Check if user already exists
                stmt = select(User).where(User.email == account["email"])
                result = await session.exec(stmt)
                existing_user = result.first()

                if existing_user:
                    logger.debug(f"⏭️  Admin user already exists: {account['email']}")
                    skipped_count += 1
                    continue

                # Create new admin user
                user = User(
                    email=account["email"],
                    hashed_password=generate_password_hash(account["password"]),
                    first_name=account["first_name"],
                    last_name=account["last_name"],
                    display_name=generate_display_name(),
                    roles=account["roles"],
                    is_active=account["is_active"],
                    is_superuser=account["is_superuser"],
                    security_question=account["security_question"],
                    security_answer=account["security_answer"],
                    account_status=account["account_status"],
                    preferred_mode="explorer",
                )

                session.add(user)
                await session.commit()

                role_names = [r.value for r in account["roles"]]
                logger.info(
                    f"✅ Created admin user: {account['email']} (roles: {', '.join(role_names)})"
                )
                created_count += 1

            except Exception as e:
                logger.error(f"❌ Failed to create admin user {account['email']}: {e}")
                await session.rollback()

        if created_count > 0:
            logger.info(
                f"🌱 Admin seeding complete: {created_count} created, {skipped_count} already existed"
            )
        else:
            logger.info(
                f"🌱 Admin seeding complete: all {skipped_count} users already exist"
            )
    finally:
        await session.close()
