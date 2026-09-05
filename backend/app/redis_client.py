"""
Redis client connection and healthcheck probe.
Connects to real Redis 7, with configurable in-memory fakeredis fallback for dev/test.
"""

from typing import AsyncGenerator, Optional, Tuple
import redis.asyncio as aioredis
from app.config import settings

_real_redis_instance: Optional[aioredis.Redis] = None
_fake_redis_instance: Optional[any] = None


async def check_redis_connection() -> Tuple[str, Optional[str]]:
    """
    Directly tests the configured Redis connection at settings.REDIS_URL.
    Returns (status, error_message):
      - ('connected', None): Real Redis is reachable and responding to PING.
      - ('mock_test_mode', err): Real Redis unreachable, but fake in-memory fallback is permitted.
      - ('unreachable', err): Real Redis unreachable, and running in production/staging or fake disallowed.
    """
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        await client.ping()
        await client.aclose()
        return "connected", None
    except Exception as e:
        is_production = settings.ENVIRONMENT.lower() in ("production", "staging")
        if is_production or not settings.ALLOW_FAKE_REDIS:
            return "unreachable", str(e)
        return "mock_test_mode", str(e)


async def get_redis_client() -> aioredis.Redis:
    """
    Returns an active Redis client. Attempts live Redis first;
    falls back to in-memory FakeRedis ONLY when permitted.
    In production, raises connection exception if live Redis is unreachable.
    """
    global _real_redis_instance, _fake_redis_instance

    if _real_redis_instance is not None:
        try:
            await _real_redis_instance.ping()
            return _real_redis_instance
        except Exception:
            _real_redis_instance = None

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        await client.ping()
        _real_redis_instance = client
        return _real_redis_instance
    except Exception:
        is_production = settings.ENVIRONMENT.lower() in ("production", "staging")
        if is_production or not settings.ALLOW_FAKE_REDIS:
            raise

        if _fake_redis_instance is None:
            import fakeredis.aioredis as fake
            _fake_redis_instance = fake.FakeRedis(decode_responses=True)
        return _fake_redis_instance


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency yielding an active Redis client."""
    client = await get_redis_client()
    yield client
