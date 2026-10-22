"""
Admin User Seeder

Creates operator-provisioned admin accounts at application startup.

KAN-498 (SEC): this module previously shipped literal credentials and fixed
security answers for two well-known admin addresses. Those literals are
removed. Provisioning now requires explicit environment-supplied values, and
startup fails closed rather than falling back to a default.
"""

from dataclasses import dataclass
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.auth.schema import (
    RoleChoicesSchema,
    SecurityQuestionsSchema,
    AccountStatusSchema,
)
from app.auth.utils import generate_password_hash, generate_display_name
from app.core.config import settings
from app.core.database import async_session
from app.core.logging import get_logger

logger = get_logger()


class AdminSeedConfigError(RuntimeError):
    """Raised when admin seeding is enabled but not fully configured."""


@dataclass(frozen=True)
class AdminAccount:
    """A single operator-provisioned admin account."""

    email: str
    password: str
    first_name: str
    last_name: str
    roles: tuple
    is_superuser: bool
    security_question: str
    security_answer: str
    account_status: str = AccountStatusSchema.ACTIVE.value
    is_active: bool = True


def _require(name: str, value: Optional[str]) -> str:
    if not value:
        raise AdminSeedConfigError(
            f"KAN-498: admin seeding is enabled but {name} is not set. "
            "Refusing to fall back to a default credential. Set the value or "
            "disable seeding with ADMIN_SEED_ENABLED=false."
        )
    return value


def build_admin_accounts() -> list:
    """
    Build the accounts to seed from settings.

    Returns an empty list when seeding is disabled. Raises
    :class:`AdminSeedConfigError` when seeding is enabled but required values
    are absent - there is deliberately no hardcoded fallback.
    """
    if not settings.ADMIN_SEED_ENABLED:
        return []

    superadmin = AdminAccount(
        email=_require(
            "ADMIN_SEED_SUPERADMIN_EMAIL", settings.ADMIN_SEED_SUPERADMIN_EMAIL
        ),
        password=_require(
            "ADMIN_SEED_SUPERADMIN_PASSWORD", settings.ADMIN_SEED_SUPERADMIN_PASSWORD
        ),
        first_name="Super",
        last_name="Admin",
        roles=(
            RoleChoicesSchema.SUPER_ADMIN,
            RoleChoicesSchema.CREATOR,
            RoleChoicesSchema.EXPLORER,
        ),
        is_superuser=True,
        security_question=SecurityQuestionsSchema.MOTHER_MAIDEN_NAME.value,
        security_answer=_require(
            "ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER",
            settings.ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER,
        ),
    )

    accounts = [superadmin]

    # The secondary admin is optional: both its email and password must be
    # supplied together, and neither may be inferred.
    if settings.ADMIN_SEED_ADMIN_EMAIL or settings.ADMIN_SEED_ADMIN_PASSWORD:
        accounts.append(
            AdminAccount(
                email=_require(
                    "ADMIN_SEED_ADMIN_EMAIL", settings.ADMIN_SEED_ADMIN_EMAIL
                ),
                password=_require(
                    "ADMIN_SEED_ADMIN_PASSWORD", settings.ADMIN_SEED_ADMIN_PASSWORD
                ),
                first_name="Platform",
                last_name="Admin",
                roles=(
                    RoleChoicesSchema.ADMIN,
                    RoleChoicesSchema.CREATOR,
                    RoleChoicesSchema.EXPLORER,
                ),
                is_superuser=False,
                security_question=SecurityQuestionsSchema.FAVORITE_COLOUR.value,
                security_answer=_require(
                    "ADMIN_SEED_ADMIN_SECURITY_ANSWER",
                    settings.ADMIN_SEED_ADMIN_SECURITY_ANSWER,
                ),
            )
        )

    return accounts


async def seed_admin_users(session: Optional[AsyncSession] = None) -> None:
    """
    Create configured admin users if they do not already exist.

    Raises :class:`AdminSeedConfigError` when seeding is enabled without
    complete configuration, so the application fails closed at startup.
    """
    accounts = build_admin_accounts()

    if not accounts:
        logger.info("Admin seeding disabled (ADMIN_SEED_ENABLED is false)")
        return

    logger.info("Checking configured admin users...")

    owns_session = session is None
    db = session if session is not None else async_session()
    try:
        created_count = 0
        skipped_count = 0

        for account in accounts:
            try:
                stmt = select(User).where(User.email == account.email)
                result = await db.exec(stmt)
                existing_user = result.first()

                if existing_user:
                    logger.debug(f"Admin user already exists: {account.email}")
                    skipped_count += 1
                    continue

                user = User(
                    email=account.email,
                    hashed_password=generate_password_hash(account.password),
                    first_name=account.first_name,
                    last_name=account.last_name,
                    display_name=generate_display_name(),
                    roles=list(account.roles),
                    is_active=account.is_active,
                    is_superuser=account.is_superuser,
                    security_question=account.security_question,
                    security_answer=account.security_answer,
                    account_status=account.account_status,
                    preferred_mode="explorer",
                )

                db.add(user)
                await db.commit()

                role_names = [r.value for r in account.roles]
                logger.info(
                    f"Created admin user: {account.email} "
                    f"(roles: {', '.join(role_names)})"
                )
                created_count += 1

            except Exception as e:
                logger.error(f"Failed to create admin user {account.email}: {e}")
                await db.rollback()

        if created_count > 0:
            logger.info(
                f"Admin seeding complete: {created_count} created, "
                f"{skipped_count} already existed"
            )
        else:
            logger.info(
                f"Admin seeding complete: all {skipped_count} users already exist"
            )
    finally:
        if owns_session:
            await db.close()
