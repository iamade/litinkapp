"""
Runtime synthetic-callback test for KAN-385/386 using respx.

Mocks outgoing Google token + userinfo endpoints only.
Backend callback, state store, DB, and cookie issuance run for real.
"""

import asyncio
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.main import app

pytestmark = pytest.mark.asyncio

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture(autouse=True)
def _clean_state_store():
    oauth_state_store.clear()
    yield
    oauth_state_store.clear()


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
        return state

    def _fake_token_response(self):
        return {
            "access_token": f"fake-google-access-{secrets.token_hex(8)}",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    def _fake_userinfo(self, email: str, sub: str, first: str, last: str):
        return {
            "sub": sub,
            "email": email,
            "email_verified": True,
            "given_name": first,
            "family_name": last,
            "picture": f"https://example.com/{sub}.png",
        }

    async def test_oauth_callback_two_distinct_accounts(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client, respx.mock:
            state1 = await self._get_real_state(client)
            state2 = await self._get_real_state(client)
            assert state1 != state2

            accounts = [
                (state1, "psq.oauth.runtime.a1@test.litinkai.com", f"google_sub_a1_{uuid.uuid4().hex[:8]}", "AdeOne", "TestA"),
                (state2, "psq.oauth.runtime.a2@test.litinkai.com", f"google_sub_a2_{uuid.uuid4().hex[:8]}", "AdeTwo", "TestB"),
            ]

            sessions = []
            for state, email, sub, first, last in accounts:
                respx.post(GOOGLE_TOKEN_URL).mock(return_value=httpx.Response(200, json=self._fake_token_response()))
                respx.get(GOOGLE_USERINFO_URL).mock(return_value=httpx.Response(200, json=self._fake_userinfo(email, sub, first, last)))

                resp = await client.get(
                    f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state}&code=synthetic-{sub}",
                    follow_redirects=False,
                )

                assert resp.status_code in (302, 307), f"Expected redirect, got {resp.status_code}: {resp.text}"
                loc = resp.headers.get("location", "")
                assert "localhost:5173" in loc, f"Unexpected redirect target: {loc}"

                access = resp.cookies.get("access_token")
                refresh = resp.cookies.get("refresh_token")
                assert access, "access_token cookie missing"
                assert refresh, "refresh_token cookie missing"

                me_resp = await client.get(
                    "/api/v1/users/me",
                    cookies={"access_token": access, "refresh_token": refresh},
                )
                assert me_resp.status_code == 200, f"/users/me failed: {me_resp.text}"
                user = me_resp.json()
                assert user["email"] == email
                assert user["first_name"] == first
                sessions.append({
                    "email": email,
                    "sub": sub,
                    "user_id": user["id"],
                    "access_cookie_prefix": access[:20],
                    "redirect": loc,
                })

            assert sessions[0]["user_id"] != sessions[1]["user_id"], "Accounts must map to distinct users"

            # State replay rejection
            respx.post(GOOGLE_TOKEN_URL).mock(return_value=httpx.Response(200, json=self._fake_token_response()))
            respx.get(GOOGLE_USERINFO_URL).mock(return_value=httpx.Response(200, json=self._fake_userinfo("replay@test.com", f"replay_{uuid.uuid4().hex[:8]}", "Replay", "User")))
            replay_resp = await client.get(
                f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state1}&code=reused",
                follow_redirects=False,
            )
            assert replay_resp.status_code == 400
            assert "CSRF" in replay_resp.json().get("detail", "")

        evidence_dir = Path("/tmp/psq_evidence")
        evidence_dir.mkdir(exist_ok=True)
        summary = {
            "test": "oauth_synthetic_callback_backend",
            "timestamp": _now_iso(),
            "commit": "dbc6d58",
            "runner": "backend ASGI / docker container litink-backend",
            "state1_len": len(state1),
            "state2_len": len(state2),
            "redirects": [s["redirect"] for s in sessions],
            "distinct_user_ids": [s["user_id"] for s in sessions],
            "distinct_emails": [s["email"] for s in sessions],
            "state_replay_rejected": True,
            "status": "PASS",
        }
        (evidence_dir / "backend_summary.json").write_text(json.dumps(summary, indent=2, default=str))
        print(json.dumps(summary, indent=2, default=str))
