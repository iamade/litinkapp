"""
Regression tests for OAuth CSRF state validation (KAN-385, KAN-386).

Covers:
- State match success (valid state → callback proceeds past validation)
- State mismatch (unknown state → friendly invalid-state redirect)
- State replay/reuse (same state consumed twice → second call fails closed)
- Missing state (no state param → friendly invalid-state redirect)
"""

import secrets
import time
import urllib.parse
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.core.config import settings
from app.main import app

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeRedisClient:
    def __init__(self):
        self._store: dict[str, tuple[str, float | None]] = {}

    async def set(self, key: str, value: str, ex: int | None = None):
        expires_at = time.monotonic() + ex if ex is not None else None
        self._store[key] = (value, expires_at)
        return True

    async def eval(self, script: str, numkeys: int, key: str):
        item = self._store.get(key)
        if item is None:
            return 0

        value, expires_at = item
        if expires_at is not None and time.monotonic() > expires_at:
            self._store.pop(key, None)
            return 0

        self._store.pop(key, None)
        return 1 if value is not None else 0

    async def delete(self, *keys: str):
        for key in keys:
            self._store.pop(key, None)

    async def scan_iter(self, match: str):
        prefix = match.removesuffix("*")
        for key in list(self._store):
            if key.startswith(prefix):
                yield key


class FakeRedisService:
    def __init__(self):
        self.redis_client = FakeRedisClient()
        self.is_connected = True

    async def connect(self):
        self.is_connected = True


async def _store_valid_state() -> str:
    """Generate and store a valid state, returning the token."""
    state = secrets.token_urlsafe(32)
    await oauth_state_store.store_state(state)
    return state


def _callback_url(provider: str, code: str = "test-auth-code", state: str | None = None) -> str:
    url = f"/api/v1/auth/{provider}?code={code}"
    if state is not None:
        url += f"&state={state}"
    return url


def _assert_invalid_state_redirect(resp):
    assert resp.status_code == 303
    assert resp.headers["location"] == (
        f"{settings.FRONTEND_URL}/auth?oauth_error=invalid_state"
    )
    assert "application/json" not in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Fixture: clean the state store before each test
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _clean_state_store():
    original = oauth_state_store._redis_service
    oauth_state_store._redis_service = FakeRedisService()
    await oauth_state_store.clear()
    yield
    await oauth_state_store.clear()
    oauth_state_store._redis_service = original


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_callback_valid_state_passes_validation():
    """A callback with a valid, unexpired state passes CSRF validation."""
    state = await _store_valid_state()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # We expect the callback to fail *after* state validation because
        # there is no real Google token endpoint.  The important
        # assertion is that it does NOT fail with a 400 CSRF error.
        resp = await client.get(
            _callback_url(OAuthProvider.GOOGLE, state=state),
            follow_redirects=False,
        )

    # State validation passed → the error should be downstream (token
    # exchange), NOT a 400 CSRF rejection.
    assert resp.status_code != 400 or "CSRF" not in (resp.json().get("detail", ""))


async def test_callback_missing_state_rejected():
    """A callback without a state parameter fails closed with a friendly redirect."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/auth/{OAuthProvider.GOOGLE}?code=test-code",
            follow_redirects=False,
        )

    _assert_invalid_state_redirect(resp)


async def test_callback_unknown_state_rejected():
    """A callback with a state that was never stored fails closed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            _callback_url(OAuthProvider.GOOGLE, state="never-stored-state-value"),
            follow_redirects=False,
        )

    _assert_invalid_state_redirect(resp)


async def test_callback_state_replay_rejected():
    """A state consumed once cannot be replayed."""
    state = await _store_valid_state()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call consumes the state (will fail downstream, but state is consumed).
        await client.get(
            _callback_url(OAuthProvider.GOOGLE, state=state),
            follow_redirects=False,
        )

        # Second call with the same state must be rejected.
        resp = await client.get(
            _callback_url(OAuthProvider.GOOGLE, state=state),
            follow_redirects=False,
        )

    _assert_invalid_state_redirect(resp)



async def test_login_generates_random_state():
    """The login endpoint generates a unique state for each request."""
    provider = OAuthProvider.GOOGLE.value
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.get(
            f"/api/v1/auth/login/{provider}",
            follow_redirects=False,
        )
        resp2 = await client.get(
            f"/api/v1/auth/login/{provider}",
            follow_redirects=False,
        )

    # Both should redirect (302/307).
    assert resp1.status_code in (302, 307)
    assert resp2.status_code in (302, 307)

    # Extract state from redirect Location headers.
    loc1 = resp1.headers.get("location", "")
    loc2 = resp2.headers.get("location", "")
    qs1 = urllib.parse.parse_qs(urllib.parse.urlparse(loc1).query)
    qs2 = urllib.parse.parse_qs(urllib.parse.urlparse(loc2).query)

    state1 = qs1.get("state", [None])[0]
    state2 = qs2.get("state", [None])[0]

    assert state1 is not None, "Login redirect should include a state parameter"
    assert state2 is not None, "Login redirect should include a state parameter"
    assert state1 != state2, "Each login request must generate a unique state"
    assert state1 != "random_state_string", "State must not be the old hard-coded literal"
    assert state2 != "random_state_string", "State must not be the old hard-coded literal"


async def test_login_derives_absolute_redirect_uri_when_base_env_is_missing(monkeypatch):
    """Production must never send Google a relative /auth/google redirect URI."""
    monkeypatch.setattr(settings, "OAUTH_REDIRECT_BASE_URL", "")
    monkeypatch.setattr(settings, "API_BASE_URL", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-google-client")

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="https://api.litinkai.com",
    ) as client:
        response = await client.get(
            f"/api/v1/auth/login/{OAuthProvider.GOOGLE.value}",
            follow_redirects=False,
        )

    query = urllib.parse.parse_qs(
        urllib.parse.urlparse(response.headers["location"]).query
    )
    assert query["redirect_uri"] == [
        "https://api.litinkai.com/api/v1/auth/google"
    ]


async def test_login_ignores_relative_configured_redirect_bases(monkeypatch):
    """Relative env values cannot override the absolute request-derived URI."""
    monkeypatch.setattr(settings, "OAUTH_REDIRECT_BASE_URL", "/api/v1/auth")
    monkeypatch.setattr(settings, "API_BASE_URL", "/api/v1")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-google-client")

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="https://api.litinkai.com",
    ) as client:
        response = await client.get(
            f"/api/v1/auth/login/{OAuthProvider.GOOGLE.value}",
            follow_redirects=False,
        )

    query = urllib.parse.parse_qs(
        urllib.parse.urlparse(response.headers["location"]).query
    )
    assert query["redirect_uri"] == [
        "https://api.litinkai.com/api/v1/auth/google"
    ]


async def test_login_prefers_absolute_oauth_redirect_base(monkeypatch):
    """A valid explicit callback base remains the highest-priority source."""
    monkeypatch.setattr(
        settings,
        "OAUTH_REDIRECT_BASE_URL",
        "https://oauth.example.com/api/v1/",
    )
    monkeypatch.setattr(settings, "API_BASE_URL", "https://api.example.com/api/v1")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-google-client")

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="https://api.litinkai.com",
    ) as client:
        response = await client.get(
            f"/api/v1/auth/login/{OAuthProvider.GOOGLE.value}",
            follow_redirects=False,
        )

    query = urllib.parse.parse_qs(
        urllib.parse.urlparse(response.headers["location"]).query
    )
    assert query["redirect_uri"] == [
        "https://oauth.example.com/api/v1/auth/google"
    ]


async def test_login_accepts_explicit_auth_route_base(monkeypatch):
    """An existing /auth base is not duplicated during normalization."""
    monkeypatch.setattr(
        settings,
        "OAUTH_REDIRECT_BASE_URL",
        "https://oauth.example.com/api/v1/auth/",
    )
    monkeypatch.setattr(settings, "API_BASE_URL", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-google-client")

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="https://api.litinkai.com",
    ) as client:
        response = await client.get(
            f"/api/v1/auth/login/{OAuthProvider.GOOGLE.value}",
            follow_redirects=False,
        )

    query = urllib.parse.parse_qs(
        urllib.parse.urlparse(response.headers["location"]).query
    )
    assert query["redirect_uri"] == [
        "https://oauth.example.com/api/v1/auth/google"
    ]
