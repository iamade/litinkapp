"""
Redis-backed OAuth CSRF state store.

OAuth state must be shared across API workers and consumed exactly once. Redis
provides the shared TTL store, while an atomic Lua GET+DEL script enforces
single-use semantics without exposing a replay window.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.core.services.redis import redis_client as default_redis_client

logger = get_logger()

DEFAULT_STATE_TTL_S = 600
STATE_KEY_PREFIX = "oauth:state:"

_CONSUME_STATE_LUA = """
local value = redis.call("GET", KEYS[1])
if value then
    redis.call("DEL", KEYS[1])
    return 1
end
return 0
"""


class OAuthStateStore:
    """Redis-backed OAuth state store with TTL and atomic single-use consume."""

    def __init__(self, redis_service: Any = default_redis_client) -> None:
        self._redis_service = redis_service

    def _key(self, state: str) -> str:
        return f"{STATE_KEY_PREFIX}{state}"

    async def _ensure_connected(self) -> bool:
        if getattr(self._redis_service, "is_connected", False):
            return getattr(self._redis_service, "redis_client", None) is not None

        connect = getattr(self._redis_service, "connect", None)
        if connect is None:
            return False

        try:
            await connect()
        except Exception as exc:
            logger.error("OAuth state Redis connection failed: %s", exc)
            return False

        return (
            getattr(self._redis_service, "is_connected", False)
            and getattr(self._redis_service, "redis_client", None) is not None
        )

    async def store_state(self, state: str, ttl_s: int = DEFAULT_STATE_TTL_S) -> None:
        """Record *state* with a Redis TTL.

        Redis failures fail closed: the login redirect can continue, but the
        callback will not validate this state later.
        """
        if not state:
            return

        try:
            if not await self._ensure_connected():
                logger.error("OAuth state Redis unavailable; state not stored")
                return

            client = self._redis_service.redis_client
            await client.set(self._key(state), "1", ex=ttl_s)
            logger.debug("OAuth state stored in Redis (ttl=%ds)", ttl_s)
        except Exception as exc:
            logger.error("OAuth state Redis store failed: %s", exc)

    async def consume_state(self, state: str) -> bool:
        """Atomically validate and consume *state* from Redis."""
        if not state:
            return False

        try:
            if not await self._ensure_connected():
                logger.error("OAuth state Redis unavailable; validation failed closed")
                return False

            client = self._redis_service.redis_client
            consumed = await client.eval(_CONSUME_STATE_LUA, 1, self._key(state))
            if bool(int(consumed)):
                logger.debug("OAuth state consumed successfully")
                return True

            logger.warning("OAuth state not found, expired, or already consumed")
            return False
        except Exception as exc:
            logger.error("OAuth state Redis consume failed: %s", exc)
            return False

    def start_janitor(self) -> None:
        """Backwards-compatible no-op; Redis TTL handles expiry."""
        logger.debug("OAuth state janitor not started; Redis TTL handles expiry")

    async def stop_janitor(self) -> None:
        """Backwards-compatible no-op; Redis TTL handles expiry."""
        logger.debug("OAuth state janitor not stopped; Redis TTL handles expiry")

    def __len__(self) -> int:
        """Backwards-compatible synchronous length helper."""
        return 0

    async def clear(self) -> None:
        """Delete OAuth state keys for tests."""
        try:
            if not await self._ensure_connected():
                return

            keys = [
                key
                async for key in self._redis_service.redis_client.scan_iter(
                    match=f"{STATE_KEY_PREFIX}*"
                )
            ]
            if keys:
                await self._redis_service.redis_client.delete(*keys)
        except Exception as exc:
            logger.error("OAuth state Redis clear failed: %s", exc)


oauth_state_store = OAuthStateStore()
