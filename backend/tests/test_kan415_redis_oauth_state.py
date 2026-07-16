import asyncio
import json
import time
import urllib.parse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.oauth_models import OAuthProvider
from app.auth.oauth_state import OAuthStateStore, oauth_state_store
from app.core.config import settings
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
        deleted = 0
        for key in keys:
            if key in self._store:
                deleted += 1
                self._store.pop(key, None)
        return deleted

    async def scan_iter(self, match: str):
        prefix = match.removesuffix("*")
        for key in list(self._store):
            item = self._store.get(key)
            if item is None:
                continue
            _, expires_at = item
            if expires_at is not None and time.monotonic() > expires_at:
                self._store.pop(key, None)
                continue
            if key.startswith(prefix):
                yield key


class FakeRedisService:
    def __init__(self, redis_client: FakeRedisClient | None = None):
        self.redis_client = redis_client or FakeRedisClient()
        self.is_connected = True

    async def connect(self):
        self.is_connected = True


class OutageRedisClient:
    async def set(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    async def eval(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    async def scan_iter(self, match: str):
        if False:
            yield None


class OutageRedisService:
    def __init__(self):
        self.redis_client = OutageRedisClient()
        self.is_connected = True

    async def connect(self):
        self.is_connected = True


@pytest_asyncio.fixture
async def fake_oauth_redis():
    original = oauth_state_store._redis_service
    fake_service = FakeRedisService()
    oauth_state_store._redis_service = fake_service
    await oauth_state_store.clear()
    yield fake_service
    await oauth_state_store.clear()
    oauth_state_store._redis_service = original


def _callback_url(state: str | None = None, code: str = "test-auth-code") -> str:
    url = f"/api/v1/auth/{OAuthProvider.GOOGLE.value}?code={code}"
    if state is not None:
        url += f"&state={urllib.parse.quote(state)}"
    return url


async def test_cross_worker_shared_store_consumes_once():
    redis_client = FakeRedisClient()
    worker_a = OAuthStateStore(FakeRedisService(redis_client))
    worker_b = OAuthStateStore(FakeRedisService(redis_client))

    await worker_a.store_state("shared-state")

    assert await worker_b.consume_state("shared-state") is True
    assert await worker_a.consume_state("shared-state") is False


async def test_state_expires_after_ttl():
    store = OAuthStateStore(FakeRedisService())

    await store.store_state("soon-expired", ttl_s=1)
    await asyncio.sleep(2)

    assert await store.consume_state("soon-expired") is False


async def test_state_replay_is_rejected():
    store = OAuthStateStore(FakeRedisService())

    await store.store_state("single-use")

    assert await store.consume_state("single-use") is True
    assert await store.consume_state("single-use") is False


async def test_redis_outage_fails_closed_and_login_still_redirects():
    store = OAuthStateStore(OutageRedisService())

    await store.store_state("not-stored")
    assert await store.consume_state("not-stored") is False

    original = oauth_state_store._redis_service
    oauth_state_store._redis_service = OutageRedisService()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/auth/login/{OAuthProvider.GOOGLE.value}",
                follow_redirects=False,
            )
    finally:
        oauth_state_store._redis_service = original

    assert response.status_code in (302, 307)
    assert "state=" in response.headers["location"]


@pytest.mark.usefixtures("fake_oauth_redis")
async def test_invalid_state_callback_returns_friendly_frontend_redirect():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            _callback_url(state="invalid-state"),
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{settings.FRONTEND_URL}/auth?oauth_error=invalid_state"
    )
    assert "application/json" not in response.headers.get("content-type", "")


@pytest.mark.usefixtures("fake_oauth_redis")
async def test_invalid_state_browser_flow_never_surfaces_raw_json():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            _callback_url(state="expired-or-missing"),
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert "application/json" not in response.headers.get("content-type", "")
    with pytest.raises(json.JSONDecodeError):
        json.loads(response.text)


@pytest.mark.usefixtures("fake_oauth_redis")
async def test_missing_state_browser_flow_never_surfaces_raw_json():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(_callback_url(state=None), follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{settings.FRONTEND_URL}/auth?oauth_error=invalid_state"
    )
    assert "application/json" not in response.headers.get("content-type", "")
