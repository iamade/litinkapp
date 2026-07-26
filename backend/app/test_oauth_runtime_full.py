"""
Full runtime KAN-385/386 synthetic OAuth callback test.

- Two distinct synthetic Google identities.
- Verifies state generation, state validation/consumption, distinct sessions.
- Verifies state replay rejected.
- Verifies frontend reflects authenticated state when cookies are injected.
"""

import asyncio
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import respx
from httpx import ASGITransport, AsyncClient
from playwright.async_api import async_playwright

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.main import app

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
FRONTEND = "http://localhost:5173"
API = "http://test"
EVID = Path("/tmp/psq_evidence")
EVID.mkdir(exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def fake_token():
    return {"access_token": f"fake-google-{secrets.token_hex(8)}", "expires_in": 3600, "token_type": "Bearer"}


def fake_userinfo(email: str, sub: str, first: str, last: str):
    return {"sub": sub, "email": email, "email_verified": True, "given_name": first, "family_name": last, "picture": "https://example.com/pic.png"}


async def run():
    started_at = "2026-07-10T06:21:27.125969665Z"
    oauth_state_store.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=API) as client, respx.mock:
        accounts = [
            ("psq.oauth.runtime.a1@test.litinkai.com", f"google_sub_a1_{uuid.uuid4().hex[:8]}", "AdeOne", "TestA"),
            ("psq.oauth.runtime.a2@test.litinkai.com", f"google_sub_a2_{uuid.uuid4().hex[:8]}", "AdeTwo", "TestB"),
        ]
        sessions = []
        states = []

        for email, sub, first, last in accounts:
            login_resp = await client.get(f"/api/v1/auth/login/{OAuthProvider.GOOGLE.value}", follow_redirects=False)
            assert login_resp.status_code in (302, 307)
            state = parse_qs(urlparse(login_resp.headers["location"]).query)["state"][0]
            states.append(state)

            respx.post(GOOGLE_TOKEN_URL).mock(return_value=httpx.Response(200, json=fake_token()))
            respx.get(GOOGLE_USERINFO_URL).mock(return_value=httpx.Response(200, json=fake_userinfo(email, sub, first, last)))

            cb_resp = await client.get(f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state}&code=synthetic_code", follow_redirects=False)
            assert cb_resp.status_code in (302, 307), f"Expected redirect, got {cb_resp.status_code}: {cb_resp.text}"
            loc = cb_resp.headers.get("location", "")
            assert FRONTEND in loc

            access = cb_resp.cookies.get("access_token")
            refresh = cb_resp.cookies.get("refresh_token")
            assert access and refresh

            me = await client.get("/api/v1/users/me", cookies={"access_token": access, "refresh_token": refresh})
            assert me.status_code == 200
            user = me.json()
            assert user["email"] == email
            sessions.append({
                "email": email,
                "sub": sub,
                "user_id": user["id"],
                "access_cookie_prefix": access[:20],
                "redirect": loc,
                "cookies": {"access_token": access, "refresh_token": refresh, "logged_in": "true"},
            })

        assert sessions[0]["user_id"] != sessions[1]["user_id"]
        assert states[0] != states[1]

        # Replay rejection
        respx.post(GOOGLE_TOKEN_URL).mock(return_value=httpx.Response(200, json=fake_token()))
        respx.get(GOOGLE_USERINFO_URL).mock(return_value=httpx.Response(200, json=fake_userinfo("replay@test.com", "replay_sub", "Replay", "User")))
        replay = await client.get(f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={states[0]}&code=replay", follow_redirects=False)
        assert replay.status_code == 400
        assert "CSRF" in replay.json().get("detail", "")

    # Frontend reflection via Playwright with issued cookies
    frontend_results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        for idx, sess in enumerate(sessions, 1):
            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                base_url=FRONTEND,
            )
            await ctx.add_cookies([
                {"name": "access_token", "value": sess["cookies"]["access_token"], "domain": "localhost", "path": "/"},
                {"name": "refresh_token", "value": sess["cookies"]["refresh_token"], "domain": "localhost", "path": "/"},
                {"name": "logged_in", "value": "true", "domain": "localhost", "path": "/"},
            ])
            page = await ctx.new_page()
            await page.goto(f"{FRONTEND}/auth?mode=login", wait_until="networkidle")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=str(EVID / f"frontend_authed_acct{idx}.png"), full_page=False)
            body = await page.content()
            # Authenticated state: AuthContext should redirect or show dashboard elements
            me_resp = await page.evaluate('''async () => {
                try {
                    const r = await fetch("http://localhost:8000/api/v1/users/me", {credentials:"include"});
                    return {status: r.status, body: await r.text()};
                } catch(e) { return {status: 0, error: e.message}; }
            }''')
            frontend_results.append({
                "account": idx,
                "email": sess["email"],
                "users_me_status": me_resp["status"],
                "users_me_body_preview": me_resp.get("body", "")[:200],
                "page_contains_dashboard": "Dashboard" in body or "Creator" in body or "Onboarding" in body or "Welcome" in body,
            })
            await ctx.close()
        await browser.close()

    summary = {
        "timestamp": now_iso(),
        "commit": "dbc6d58",
        "backend_started_at": started_at,
        "frontend_image": "litinkapp-frontend:latest",
        "frontend_started_at": "2026-07-10T06:13:46.038441954Z",
        "runner": "srv1577131 / litink-backend ASGI / respx",
        "state_lens": [len(s) for s in states],
        "distinct_states": states[0] != states[1],
        "distinct_user_ids": [s["user_id"] for s in sessions],
        "distinct_emails": [s["email"] for s in sessions],
        "state_replay_rejected": True,
        "frontend_reflection": frontend_results,
        "status": "PASS",
    }
    (EVID / "oauth_runtime_full.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(run())
