# shared.cache — Redis Client

## Purpose

Provides a lazily-initialised, shared `redis.asyncio.Redis` client. All services that need Redis (rate limiting, token caching, idempotency keys, distributed locks) use this module rather than creating their own connection pools.

## Usage

```python
from shared.cache import get_redis

redis = get_redis()

# Cache a value with 5-minute TTL
await redis.set("file:status:abc123", "ready", ex=300)

# Retrieve
status = await redis.get("file:status:abc123")   # str or None

# Delete
await redis.delete("file:status:abc123")

# Atomic increment (for rate limiting counters)
count = await redis.incr("ratelimit:org123:upload")
await redis.expire("ratelimit:org123:upload", 60)
```

## Lifecycle

Call `close_redis()` once in the FastAPI lifespan shutdown to drain the connection pool cleanly:

```python
from shared.cache import close_redis

@asynccontextmanager
async def lifespan(app):
    yield
    await close_redis()
```

## Key patterns used in FileNest

| Pattern | Key format | TTL |
|---------|-----------|-----|
| Upload token cache | `upload_token:<token_id>` | 1 hour |
| Rate limit counter | `ratelimit:<org_id>:<action>` | 60 s |
| Idempotency key | `idempotency:<key>` | 24 hours |
| Processing lock | `lock:processing:<file_id>` | 30 s |

## Notes

- The client is configured with `decode_responses=True` — all values are Python strings, not bytes.
- Do not store binary data (file bytes, encrypted blobs) in Redis — use object storage.
- In dev, Redis runs via `docker compose` on `localhost:6379`.
