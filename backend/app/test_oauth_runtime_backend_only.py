"""
Backend-only runtime KAN-385/386 synthetic OAuth callback test.
Writes session cookies to /tmp/psq_evidence for host-side frontend reflection.
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

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.main import app

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
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
            assert login_resp.status_code in (302, 307), f"login failed: {login_resp.status_code}"
            state = parse_qs(urlparse(login_resp.headers["location"]).query)["state"][0]
            states.append(state)

            respx.post(GOOGLE_TOKEN_URL).mock(return_value=httpx.Response(200, json=fake_token()))
            respx.get(GOOGLE_USERINFO_URL).mock(return_value=httpx.Response(200, json=fake_userinfo(email, sub, first, last)))

            cb_resp = await client.get(f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state}&code=synthetic_code", follow_redirects=False)
            assert cb_resp.status_code in (302, 307), f"callback failed: {cb_resp.status_code}: {cb_resp.text}"
            loc = cb_resp.headers.get("location", "")
            assert "localhost:5173" in loc, f"unexpected redirect: {loc}"

            access = cb_resp.cookies.get("access_token")
            refresh = cb_resp.cookies.get("refresh_token")
            assert access and refresh, "cookies missing"

            me = await client.get("/api/v1/users/me", cookies={"access_token": access, "refresh_token": refresh})
            assert me.status_code == 200, f"/users/me failed: {me.text}"
            user = me.json()
            assert user["email"] == email
            sessions.append({
                "email": email,
                "sub": sub,
                "user_id": user["id"],
                "first_name": user["first_name"],
                "access_cookie": access,
                "refresh_cookie": refresh,
                "redirect": loc,
            })

        assert sessions[0]["user_id"] != sessions[1]["user_id"]
        assert states[0] != states[1]

        # Replay rejection
        respx.post(GOOGLE_TOKEN_URL).mock(return_value=httpx.Response(200, json=fake_token()))
        respx.get(GOOGLE_USERINFO_URL).mock(return_value=httpx.Response(200, json=fake_userinfo("replay@test.com", "replay_sub", "Replay", "User")))
        replay = await client.get(f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={states[0]}&code=replay", follow_redirects=False)
        assert replay.status_code == 400
        assert "CSRF" in replay.json().get("detail", "")

    summary = {
        "timestamp": now_iso(),
        "commit": "dbc6d58",
        "backend_started_at": started_at,
        "runner": "litink-backend ASGI / respx",
        "state_lens": [len(s) for s in states],
        "distinct_states": states[0] != states[1],
        "distinct_user_ids": [s["user_id"] for s in sessions],
        "distinct_emails": [s["email"] for s in sessions],
        "state_replay_rejected": True,
        "sessions": sessions,
        "status": "PASS",
    }
    (EVID / "oauth_runtime_backend.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(run())
