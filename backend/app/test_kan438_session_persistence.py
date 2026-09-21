"""
KAN-438: Session-Cookie Persistence Tests (mocked DB — no live DB required).
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.database import get_session

TEST_USER_ID = uuid.uuid4()


def make_jwt(token_type="access_token", expired=False):
    if token_type == settings.COOKIE_ACCESS_NAME:
        delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES)
    else:
        delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRATION_DAYS)
    if expired:
        delta = -timedelta(hours=1)
    payload = {
        "id": str(TEST_USER_ID),
        "type": token_type,
        "exp": datetime.now(timezone.utc) + delta,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SIGNING_KEY, algorithm=settings.JWT_ALGORITHM)


def make_mock_user():
    u = MagicMock()
    u.id = TEST_USER_ID
    u.email = "test@litinkai.com"
    u.is_active = True
    u.display_name = "Test User"
    u.roles = ["user"]
    return u


async def mock_get_session():
    yield MagicMock()


async def run_tests():
    results = []
    app.dependency_overrides[get_session] = mock_get_session
    mock_user = make_mock_user()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "app.api.routes.auth.session.user_auth_service.get_user_by_id",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            # TEST 1: Valid access → 200
            client.cookies.clear()
            r = await client.get("/api/v1/auth/session",
                cookies={settings.COOKIE_ACCESS_NAME: make_jwt()})
            if r.status_code == 200 and r.json().get("is_authenticated"):
                results.append(("PASS", "Valid access_token → 200"))
            else:
                results.append(("FAIL", f"Valid access: {r.status_code} {r.text[:100]}"))

            # TEST 2: Expired access + valid refresh → 200 + new cookie
            client.cookies.clear()
            r = await client.get("/api/v1/auth/session",
                cookies={
                    settings.COOKIE_ACCESS_NAME: make_jwt(expired=True),
                    settings.COOKIE_REFRESH_NAME: make_jwt(token_type=settings.COOKIE_REFRESH_NAME),
                })
            new_ck = r.cookies.get(settings.COOKIE_ACCESS_NAME)
            if r.status_code == 200 and new_ck:
                results.append(("PASS", "Refresh-on-expiry → 200 + new cookie"))
            else:
                results.append(("FAIL", f"Refresh: {r.status_code} cookie={bool(new_ck)}"))

            # TEST 3: No cookies → 401
            client.cookies.clear()
            r = await client.get("/api/v1/auth/session")
            if r.status_code == 401:
                results.append(("PASS", "No cookies → 401"))
            else:
                results.append(("FAIL", f"No cookies: expected 401, got {r.status_code}"))

            # TEST 4: Expired access + no refresh → 401
            client.cookies.clear()
            r = await client.get("/api/v1/auth/session",
                cookies={settings.COOKIE_ACCESS_NAME: make_jwt(expired=True)})
            if r.status_code == 401:
                results.append(("PASS", "Expired access, no refresh → 401"))
            else:
                results.append(("FAIL", f"Expired no refresh: expected 401, got {r.status_code}"))

            # TEST 5: Valid access + expired refresh → 200
            client.cookies.clear()
            r = await client.get("/api/v1/auth/session",
                cookies={
                    settings.COOKIE_ACCESS_NAME: make_jwt(),
                    settings.COOKIE_REFRESH_NAME: make_jwt(token_type=settings.COOKIE_REFRESH_NAME, expired=True),
                })
            if r.status_code == 200 and r.json().get("is_authenticated"):
                results.append(("PASS", "Valid access + expired refresh → 200"))
            else:
                results.append(("FAIL", f"Valid+expired refresh: {r.status_code}"))

    app.dependency_overrides.clear()
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("KAN-438: Session-Cookie Persistence Tests")
    print("=" * 60)
    results = asyncio.run(run_tests())
    p = sum(1 for s, _ in results if s == "PASS")
    f = sum(1 for s, _ in results if s == "FAIL")
    for s, msg in results:
        print(f"  {'✅' if s == 'PASS' else '❌'} [{s}] {msg}")
    print("-" * 60)
    print(f"Total: {len(results)} | Pass: {p} | Fail: {f}")
    sys.exit(1 if f else 0)
