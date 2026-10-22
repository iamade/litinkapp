"""KAN-498 (SEC): admin seeding must not ship or accept default credentials.

Defect (pre-fix): ``app/core/admin_seeder.py`` carried a module-level
``ADMIN_ACCOUNTS`` list with literal passwords and literal security answers for
two well-known admin addresses. Because ``main.lifespan`` calls
``seed_admin_users()`` on every startup, a fresh deployment silently created
superuser/admin accounts whose credentials were public in the repository.

Required behaviour after the fix:
  (a) no hardcoded fallback is accepted - when seeding is enabled without
      complete operator-supplied configuration, startup fails closed with a
      clear error instead of creating an account with a default password;
  (b) an admin is seeded only when explicit env-provided values are present.

These tests run without a database: ``build_admin_accounts`` is pure, and the
seeded-user path uses a fake async session.
"""

import os

# Import-time settings singletons read the environment; supply collection-safe
# dummies before any app.* import (see backend/tests/conftest.py for the reason).
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REDIS_URL", "CELERY_BROKER_URL"]:
    os.environ.setdefault(_k, "dummy")
os.environ.setdefault("SMTP_PORT", "0")

import pathlib

import pytest

from app.core import admin_seeder
from app.core.admin_seeder import (
    AdminSeedConfigError,
    build_admin_accounts,
    seed_admin_users,
)


SEEDER_PATH = pathlib.Path(admin_seeder.__file__)
SEED_SETTINGS = (
    "ADMIN_SEED_ENABLED",
    "ADMIN_SEED_SUPERADMIN_EMAIL",
    "ADMIN_SEED_SUPERADMIN_PASSWORD",
    "ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER",
    "ADMIN_SEED_ADMIN_EMAIL",
    "ADMIN_SEED_ADMIN_PASSWORD",
    "ADMIN_SEED_ADMIN_SECURITY_ANSWER",
)


@pytest.fixture(autouse=True)
def _clean_seed_settings(monkeypatch):
    """Start every test from a known, fully-unset seeding configuration."""
    from app.core.config import settings

    for name in SEED_SETTINGS:
        default = False if name == "ADMIN_SEED_ENABLED" else ""
        monkeypatch.setattr(settings, name, default, raising=True)
    yield


# --------------------------------------------------------------------------
# (a) No hardcoded fallback is accepted
# --------------------------------------------------------------------------


def test_seeder_source_carries_no_credential_literal():
    """The module must not re-introduce a literal password or security answer."""
    source = SEEDER_PATH.read_text()

    assert "password123" not in source, "known default password literal returned"
    # The old module hardcoded these as literal security answers.
    assert '"password":' not in source, "literal password assignment returned"
    assert '"security_answer":' not in source, "literal security answer returned"


def test_disabled_seeding_builds_no_accounts():
    """Default posture: seeding off, no accounts, no error."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = False

    assert build_admin_accounts() == []


def test_enabled_without_password_fails_closed():
    """Enabled but missing the password must raise, never invent one."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = True
    settings.ADMIN_SEED_SUPERADMIN_EMAIL = "ops@example.test"
    settings.ADMIN_SEED_SUPERADMIN_PASSWORD = ""
    settings.ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER = "answer"

    with pytest.raises(AdminSeedConfigError) as excinfo:
        build_admin_accounts()

    assert "ADMIN_SEED_SUPERADMIN_PASSWORD" in str(excinfo.value)


def test_enabled_without_email_fails_closed():
    """Enabled but missing the email must raise."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = True
    settings.ADMIN_SEED_SUPERADMIN_EMAIL = ""
    settings.ADMIN_SEED_SUPERADMIN_PASSWORD = "env-provided-secret"
    settings.ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER = "answer"

    with pytest.raises(AdminSeedConfigError) as excinfo:
        build_admin_accounts()

    assert "ADMIN_SEED_SUPERADMIN_EMAIL" in str(excinfo.value)


def test_enabled_without_security_answer_fails_closed():
    """Security answer has no default either."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = True
    settings.ADMIN_SEED_SUPERADMIN_EMAIL = "ops@example.test"
    settings.ADMIN_SEED_SUPERADMIN_PASSWORD = "env-provided-secret"
    settings.ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER = ""

    with pytest.raises(AdminSeedConfigError):
        build_admin_accounts()


@pytest.mark.parametrize("setting", ["ADMIN_SEED_SUPERADMIN_EMAIL", "ADMIN_SEED_SUPERADMIN_PASSWORD"])
def test_settings_defaults_are_empty_not_literal(setting):
    """The settings model itself must not declare a usable default credential."""
    from app.core.config import Settings

    field = Settings.model_fields[setting]

    assert field.default == "", f"{setting} must default to empty, not a credential"


# --------------------------------------------------------------------------
# (b) An admin exists only with env-provided values
# --------------------------------------------------------------------------


def test_build_uses_env_values_verbatim():
    """Configured values are used as given - nothing is substituted."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = True
    settings.ADMIN_SEED_SUPERADMIN_EMAIL = "root@example.test"
    settings.ADMIN_SEED_SUPERADMIN_PASSWORD = "s3cret-from-env"
    settings.ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER = "green"

    accounts = build_admin_accounts()

    assert len(accounts) == 1
    assert accounts[0].email == "root@example.test"
    assert accounts[0].password == "s3cret-from-env"
    assert accounts[0].security_answer == "green"
    assert accounts[0].is_superuser is True


def test_secondary_admin_requires_both_values():
    """Supplying only the secondary email must raise rather than half-seed."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = True
    settings.ADMIN_SEED_SUPERADMIN_EMAIL = "root@example.test"
    settings.ADMIN_SEED_SUPERADMIN_PASSWORD = "s3cret-from-env"
    settings.ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER = "green"
    settings.ADMIN_SEED_ADMIN_EMAIL = "platform@example.test"
    settings.ADMIN_SEED_ADMIN_PASSWORD = ""

    with pytest.raises(AdminSeedConfigError) as excinfo:
        build_admin_accounts()

    assert "ADMIN_SEED_ADMIN_PASSWORD" in str(excinfo.value)


class _FakeResult:
    def __init__(self, first=None):
        self._first = first

    def first(self):
        return self._first


class _FakeSession:
    """Minimal async session capturing whether a user was added."""

    def __init__(self):
        self.added = []
        self.committed = 0
        self.rolled_back = 0
        self.closed = 0

    async def exec(self, stmt):
        return _FakeResult(None)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1

    async def close(self):
        self.closed += 1


@pytest.mark.asyncio
async def test_seeding_creates_admin_only_with_env_values():
    """With env values present, exactly one admin user is created."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = True
    settings.ADMIN_SEED_SUPERADMIN_EMAIL = "root@example.test"
    settings.ADMIN_SEED_SUPERADMIN_PASSWORD = "s3cret-from-env"
    settings.ADMIN_SEED_SUPERADMIN_SECURITY_ANSWER = "green"

    session = _FakeSession()
    await seed_admin_users(session=session)

    assert len(session.added) == 1
    created = session.added[0]
    assert created.email == "root@example.test"
    assert created.is_superuser is True
    assert session.committed == 1
    # Caller owns the injected session; the seeder must not close it.
    assert session.closed == 0


@pytest.mark.asyncio
async def test_seeding_disabled_creates_nothing():
    """Seeding off means no user rows, regardless of DB state."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = False

    session = _FakeSession()
    await seed_admin_users(session=session)

    assert session.added == []
    assert session.committed == 0


@pytest.mark.asyncio
async def test_startup_fails_closed_when_values_absent():
    """The startup path raises instead of creating a default-credential admin."""
    from app.core.config import settings

    settings.ADMIN_SEED_ENABLED = True
    settings.ADMIN_SEED_SUPERADMIN_EMAIL = ""
    settings.ADMIN_SEED_SUPERADMIN_PASSWORD = ""

    session = _FakeSession()
    with pytest.raises(AdminSeedConfigError):
        await seed_admin_users(session=session)

    # The critical assertion: no account was written before the failure.
    assert session.added == []
    assert session.committed == 0
