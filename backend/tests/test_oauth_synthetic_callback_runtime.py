"""
Runtime synthetic-callback test for KAN-385/386.

Runs inside the backend container (or via ASGI) and mocks the Google
/token + /userinfo calls so the full callback path executes without
real Google credentials.

Covers:
- Real CSRF state obtained from /auth/login/google.
- State validation + consumption at /auth/google.
- Unknown Google identities redirect to registration instead of being auto-created.
- State replay rejected.
"""

import secrets
import uuid
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.main import app

pytestmark = pytest.mark.asyncio


def _fake_token_response():
    return {
        "access_token": f"fake-google-access-{secrets.token_hex(8)}",
        "expires_in": 3600,
        "token_type": "Bearer",
    }


def _fake_userinfo(email: str, sub: str, first: str, last: str):
    return {
        "sub": sub,
        "email": email,
        "email_verified": True,
        "given_name": first,
        "family_name": last,
        "picture": f"https://example.com/{sub}.png",
    }


@pytest_asyncio.fixture(autouse=True)
async def _clean_state_store():
    # Swap in an in-memory fake Redis so the runtime callback flow works
    # without a live Redis (mirrors tests/test_kan385_386_oauth_csrf_state.py).
    from tests.test_kan385_386_oauth_csrf_state import FakeRedisService

    oauth_state_store._redis_service = FakeRedisService()
    try:
        await oauth_state_store.clear()
        yield
    finally:
        await oauth_state_store.clear()


class _EmptyResult:
    """Mimics a SQL result with no rows (unknown email, no OAuth link)."""

    def first(self):
        return None


class _UnknownAccountSession:
    """Session stub that always reports no existing account for KAN-463."""

    def __init__(self):
        self.added = []
        self.commits = 0

    async def exec(self, statement):
        return _EmptyResult()

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        return None


@pytest_asyncio.fixture(autouse=True)
def _unknown_account_session():
    # The callback route uses the real get_session dependency, which would
    # dial a live database. Redirect assertions only need a session that
    # reports "no account exists", so swap in an in-memory stub and restore
    # the original wiring afterwards.
    from app.core.database import get_session

    fake = _UnknownAccountSession()
    app.dependency_overrides[get_session] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_session, None)


class TestOAuthSyntheticCallbackRuntime:

    async def _get_real_state(self, client: AsyncClient) -> str:
        resp = await client.get(
            f"/api/v1/auth/login/{OAuthProvider.GOOGLE.value}",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        loc = resp.headers["location"]
        qs = parse_qs(urlparse(loc).query)
        state = qs["state"][0]
        assert len(state) >= 43
        return state, loc

    async def _mock_google_exchange(self, email: str, sub: str, first: str, last: str):
        token_res = httpx.Response(200, json=_fake_token_response())
        userinfo_res = httpx.Response(200, json=_fake_userinfo(email, sub, first, last))

        # Patch only the OAuth route's httpx client constructor, returning a
        # fully mocked instance. Patching httpx.AsyncClient methods globally
        # would also intercept this test's own ASGI client and break the
        # callback request with a 404.
        def mock_client_factory(*args, **kwargs):
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post = AsyncMock(return_value=token_res)
            instance.get = AsyncMock(return_value=userinfo_res)
            return instance

        return patch("app.api.routes.auth.oauth.httpx.AsyncClient", mock_client_factory)

    async def test_oauth_callback_unknown_google_accounts_redirect_to_register(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            state1, loc1 = await self._get_real_state(client)
            state2, loc2 = await self._get_real_state(client)
            assert state1 != state2, "Each login must generate a unique state"

            accounts = [
                (state1, "psq.oauth.runtime.a1@test.litinkai.com", f"google_sub_a1_{uuid.uuid4().hex[:8]}", "AdeOne", "TestA"),
                (state2, "psq.oauth.runtime.a2@test.litinkai.com", f"google_sub_a2_{uuid.uuid4().hex[:8]}", "AdeTwo", "TestB"),
            ]

            redirects = []
            for state, email, sub, first, last in accounts:
                p_client = await self._mock_google_exchange(email, sub, first, last)
                with p_client:
                    resp = await client.get(
                        f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state}&code=synthetic-{sub}",
                        follow_redirects=False,
                    )
                assert resp.status_code == 303, f"Expected redirect, got {resp.status_code}: {resp.text}"
                loc = resp.headers.get("location", "")
                parsed = urlparse(loc)
                query = parse_qs(parsed.query)
                assert parsed.path == "/auth"
                assert query == {
                    "mode": ["register"],
                    "oauth_error": ["account_unavailable"],
                    "email": [email],
                }
                assert resp.cookies.get("access_token") is None
                assert resp.cookies.get("refresh_token") is None
                redirects.append(loc)

            assert redirects[0] != redirects[1], "Distinct emails must remain distinct in redirect query params"

            # State replay rejection
            p_client = await self._mock_google_exchange(
                "replay@test.litinkai.com", f"replay_{uuid.uuid4().hex[:8]}", "Replay", "User"
            )
            with p_client:
                replay_resp = await client.get(
                    f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state1}&code=reused",
                    follow_redirects=False,
                )
            assert replay_resp.status_code == 303
            assert replay_resp.headers["location"].endswith("/auth?oauth_error=invalid_state")
