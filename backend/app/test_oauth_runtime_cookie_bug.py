"""
Evidence test for KAN-385/386 runtime OAuth callback.

Uses respx to mock Google's token + userinfo endpoints so the full
backend callback path executes without real Google credentials.

This test documents a bug: the callback returns a RedirectResponse but
calls set_auth_cookies() on the response parameter, so the issued
session cookies are NOT attached to the redirect. The frontend therefore
receives no access_token/refresh_token and remains unauthenticated.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import respx
from httpx import ASGITransport, AsyncClient

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.main import app

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
EVID = Path("/tmp/psq_evidence")
EVID.mkdir(exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def main():
    oauth_state_store.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client, respx.mock:
        # 1. Obtain real CSRF state from login endpoint
        login_resp = await client.get(
            f"/api/v1/auth/login/{OAuthProvider.GOOGLE.value}",
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 307)
        loc = login_resp.headers.get("location", "")
        state = parse_qs(urlparse(loc).query).get("state", [None])[0]

        # 2. Mock Google endpoints
        respx.post(GOOGLE_TOKEN_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "fake", "expires_in": 3600, "token_type": "Bearer"})
        )
        respx.get(GOOGLE_USERINFO_URL).mock(
            return_value=httpx.Response(200, json={
                "sub": "psq_runtime_sub_1",
                "email": "psq.oauth.runtime.1@test.litinkai.com",
                "given_name": "Runtime",
                "family_name": "One",
                "picture": "https://example.com/pic.png",
            })
        )

        # 3. Trigger backend callback with synthetic code
        cb_resp = await client.get(
            f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state}&code=synthetic_runtime_1",
            follow_redirects=False,
        )

        headers = dict(cb_resp.headers)
        set_cookie = headers.get("set-cookie", "")
        location = headers.get("location", "")
        cookies = dict(cb_resp.cookies)

        print("=" * 60)
        print("KAN-385/386 Runtime OAuth callback evidence")
        print("=" * 60)
        print(f"callback status: {cb_resp.status_code}")
        print(f"location: {location}")
        print(f"set-cookie header present: {bool(set_cookie)}")
        print(f"set-cookie preview: {set_cookie[:200]}")
        print(f"parsed cookies: {cookies}")
        print(f"access_token cookie: {cookies.get('access_token')}")
        print(f"refresh_token cookie: {cookies.get('refresh_token')}")

        summary = {
            "timestamp": now_iso(),
            "commit": "dbc6d58",
            "runner": "backend ASGI / litink-backend container",
            "login_status": login_resp.status_code,
            "state_len": len(state),
            "callback_status": cb_resp.status_code,
            "callback_location": location,
            "set_cookie_header": set_cookie,
            "parsed_cookies": cookies,
            "access_token_cookie": cookies.get("access_token"),
            "refresh_token_cookie": cookies.get("refresh_token"),
            "bug": "set_auth_cookies called on response param, but RedirectResponse returned — cookies dropped",
            "verdict": "FAIL" if not cookies.get("access_token") else "PASS",
        }
        (EVID / "oauth_cookie_bug.json").write_text(json.dumps(summary, indent=2, default=str))
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
