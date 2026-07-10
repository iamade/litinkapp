"""
Unit test for KAN-385/386: OAuth callback must preserve Set-Cookie headers.

This test mocks the nested httpx.AsyncClient used inside the callback at the
import site (`app.api.routes.auth.oauth.httpx`) so the callback can complete
without real network calls, then asserts the returned response carries the
redirect status, Location header, and the auth cookies set by set_auth_cookies.
"""

import asyncio
import secrets
from unittest.mock import AsyncMock, patch

import httpx
from httpx import ASGITransport, AsyncClient

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.main import app


def _store_valid_state() -> str:
    state = secrets.token_urlsafe(32)
    oauth_state_store.store_state(state)
    return state


async def main():
    oauth_state_store.clear()
    state = _store_valid_state()

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

    print(f"status={resp.status_code}")
    print(f"location={location}")
    print(f"set_cookie_names={cookie_names}")
    print("PASS: OAuth redirect preserves auth cookies")


if __name__ == "__main__":
    asyncio.run(main())
