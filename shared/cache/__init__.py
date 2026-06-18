"""
shared.cache — Async Redis client singleton.

Provides a lazily-initialised `redis.asyncio.Redis` client shared across the
process. Call `get_redis()` anywhere to obtain the client; call `close_redis()`
once in the FastAPI lifespan shutdown handler to cleanly drain the connection
pool.

The client is configured with `decode_responses=True` so all values are
returned as Python strings, not bytes. If you need raw bytes (e.g. for storing
binary blobs), create a separate client directly — do not change this default.

Usage:
    from shared.cache import get_redis

    redis = get_redis()
    await redis.set("key", "value", ex=300)
    value = await redis.get("key")
"""
import redis.asyncio as aioredis

from shared.config import settings

# Module-level singleton; initialised on first call to get_redis()
_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """
    Return the shared async Redis client, creating it on first call.

    The connection pool is managed internally by redis-py and connections are
    returned to the pool after each command. This function is safe to call
    repeatedly — it always returns the same client instance.
    """
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    """
    Close the Redis connection pool.

    Call once during FastAPI lifespan shutdown to allow in-flight commands to
    complete before the process exits.
    """
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
