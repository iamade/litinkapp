"""KAN-470 / KAN-471: auth error-response hardening tests.

KAN-470 (P1): POST /api/v1/auth/register (and login) 422 validation errors
must NEVER echo the submitted password (or any sensitive field value) back
in the response. Fixed by a global sanitized RequestValidationError handler
in app/main.py that rebuilds error entries from safe fields only
(loc/msg/type/error_code) and drops pydantic `input` values entirely.

KAN-471 (P2): login failures must be machine-distinguishable. Every login
failure path now carries an `error_code` discriminator:
- VALIDATION_ERROR_* family (422, from the sanitized handler)
- INVALID_CREDENTIALS (401, wrong password AND unknown email — kept
  identical to prevent account enumeration; previously unknown email
  returned a vague 200)
- ACCOUNT_INACTIVE (400), ACCOUNT_LOCKED (400, from user_auth service)
"""

import os

# Test-safe env BEFORE app imports (same pattern as the leak-repro probe).
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in [
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "REDIS_URL", "CELERY_BROKER_URL",
]:
    os.environ.setdefault(_k, "dummy" if "PORT" not in _k else "0")

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import app

pytestmark = pytest.mark.asyncio

LEAK_PASSWORD = "LeakMe1"
SHORT_PASSWORD = "Short1"

client = TestClient(app, raise_server_exceptions=False)


class _FakeResult:
    def __init__(self, first=None):
        self._first = first

    def first(self):
        return self._first


class _FakeSession:
    """Queued-result fake session (mirrors test_kan146 pattern)."""

    def __init__(self, results):
        self._results = list(results)
        self.commits = 0

    async def exec(self, statement):
        if not self._results:
            raise AssertionError(f"Unexpected query: {statement}")
        return self._results.pop(0)

    def add(self, item):
        pass

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        pass


def _no_user_session():
    return _FakeSession([_FakeResult(first=None)])


# ---------------------------------------------------------------------------
# KAN-470: no submitted value ever appears in a 422 response
# ---------------------------------------------------------------------------

async def test_register_422_never_echoes_submitted_password():
    """THE KAN-470 defect: short password -> 422 that echoed 'LeakMe1'."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "leakprobe@example.com",
            "password": SHORT_PASSWORD,
            "confirm_password": SHORT_PASSWORD,
            "first_name": "L",
            "last_name": "P",
        },
    )
    assert r.status_code == 422
    assert LEAK_PASSWORD not in r.text, "password leaked in 422 body"
    assert '"input"' not in r.text, "raw pydantic input field present"
    body = r.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    codes = {e["error_code"] for e in body["detail"]}
    assert "VALIDATION_ERROR_PASSWORD_POLICY" in codes


async def test_login_422_never_echoes_submitted_password():
    """Same leak class on the login endpoint (same handler)."""
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "someone@example.com", "password": SHORT_PASSWORD},
    )
    assert r.status_code == 422
    assert LEAK_PASSWORD not in r.text, "password leaked in 422 body"
    assert '"input"' not in r.text
    body = r.json()
    codes = {e["error_code"] for e in body["detail"]}
    assert "VALIDATION_ERROR_PASSWORD_POLICY" in codes


async def test_register_422_no_input_echo_for_any_field():
    """Non-sensitive values must not be echoed either (uniform sanitizer)."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "ValidPass99",
            "confirm_password": "ValidPass99",
        },
    )
    assert r.status_code == 422
    assert "not-an-email" not in r.text
    assert "ValidPass99" not in r.text
    assert '"input"' not in r.text
    body = r.json()
    codes = {e["error_code"] for e in body["detail"]}
    assert "VALIDATION_ERROR_EMAIL_FORMAT" in codes


# ---------------------------------------------------------------------------
# KAN-471: login failure paths are machine-distinguishable
# ---------------------------------------------------------------------------

async def test_login_malformed_json_distinguishable():
    r = client.post(
        "/api/v1/auth/login",
        content=b"{broken json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    codes = {e["error_code"] for e in body["detail"]}
    assert "VALIDATION_ERROR_MALFORMED_JSON" in codes


async def test_login_missing_field_distinguishable():
    r = client.post("/api/v1/auth/login", json={"email": "someone@example.com"})
    assert r.status_code == 422
    body = r.json()
    codes = {e["error_code"] for e in body["detail"]}
    assert "VALIDATION_ERROR_MISSING_FIELD" in codes


async def test_login_unknown_email_returns_401_invalid_credentials():
    """Previously a vague 200 — now the SAME 401 shape as wrong-password."""
    app.dependency_overrides[get_session] = _session_override_factory(
        _FakeSession([_FakeResult(first=None)])
    )
    try:
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "Whatever123"},
        )
    finally:
        app.dependency_overrides.pop(get_session, None)
    assert r.status_code == 401
    body = r.json()["detail"]
    assert body["error_code"] == "INVALID_CREDENTIALS"
    assert body["status"] == "error"
    assert "remaining_attempts" in body


def _session_override_factory(fake):
    async def _override():
        yield fake

    return _override


async def test_login_wrong_password_returns_401_invalid_credentials():
    """Wrong-password path keeps 401 + INVALID_CREDENTIALS (KAN-471)."""
    from app.auth.models import User

    user = User(email="known@example.com")
    user.hashed_password = "not-a-real-hash-but-verify-will-fail"
    user.is_active = True
    user.failed_login_attempts = 0
    app.dependency_overrides[get_session] = _session_override_factory(
        _FakeSession([_FakeResult(first=user)])
    )
    try:
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "known@example.com", "password": "WrongPass123"},
        )
    finally:
        app.dependency_overrides.pop(get_session, None)
    assert r.status_code == 401
    body = r.json()["detail"]
    assert body["error_code"] == "INVALID_CREDENTIALS"
    assert "remaining_attempts" in body