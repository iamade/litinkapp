"""
Unit test for KAN-385/386: OAuth callback must preserve Set-Cookie headers.

This test mocks the nested httpx.AsyncClient used inside the callback at the
import site (`app.api.routes.auth.oauth.httpx`) so the callback can complete
without real network calls, then asserts the returned response carries the
redirect status, Location header, and the auth cookies set by set_auth_cookies.
"""

import secrets
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.core.database import get_session
from app.main import app


pytestmark = pytest.mark.asyncio


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


class _EmptyResult:
    def first(self):
        return None


class FakeSession:
    def __init__(self):
        self.added = []

    async def exec(self, statement):
        return _EmptyResult()

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        return None

    async def refresh(self, item):
        return None


@pytest_asyncio.fixture(autouse=True)
async def _fake_oauth_state_store():
    original = oauth_state_store._redis_service
    oauth_state_store._redis_service = FakeRedisService()
    app.dependency_overrides[get_session] = lambda: FakeSession()
    await oauth_state_store.clear()
    yield
    await oauth_state_store.clear()
    app.dependency_overrides.pop(get_session, None)
    oauth_state_store._redis_service = original


async def _store_valid_state() -> str:
    state = secrets.token_urlsafe(32)
    await oauth_state_store.store_state(state)
    return state


async def test_oauth_callback_redirect_preserves_auth_cookies():
    """KAN-385/386: the injected response must carry Set-Cookie on 307 redirect."""
    await oauth_state_store.clear()
    state = await _store_valid_state()

    token_res = httpx.Response(
        200,
        json={
            "access_token": f"fake-google-access-{secrets.token_hex(8)}",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
    )
    userinfo_res = httpx.Response(
        200,
        json={
            "sub": f"google_sub_{secrets.token_hex(8)}",
            "email": f"unit.cookie.{secrets.token_hex(4)}@test.litinkai.com",
            "email_verified": True,
            "given_name": "Cookie",
            "family_name": "Test",
            "picture": "https://example.com/pic.png",
        },
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.api.routes.auth.oauth.httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post = AsyncMock(return_value=token_res)
            instance.get = AsyncMock(return_value=userinfo_res)

            resp = await client.get(
                f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state}&code=fake-auth-code",
                follow_redirects=False,
            )

    assert resp.status_code in (302, 307), f"Expected redirect, got {resp.status_code}: {resp.text}"
    location = resp.headers.get("location", "")
    assert "localhost:5173" in location, f"Unexpected redirect target: {location}"

    set_cookie_headers = resp.headers.get_list("set-cookie")
    cookie_names = [c.split("=", 1)[0] for c in set_cookie_headers if "=" in c]
    assert "access_token" in cookie_names, f"access_token cookie missing: {set_cookie_headers}"
    assert "refresh_token" in cookie_names, f"refresh_token cookie missing: {set_cookie_headers}"
    assert "logged_in" in cookie_names, f"logged_in cookie missing: {set_cookie_headers}"
