# shared — Overview

## Purpose

`shared` is the internal Python library that every FileNest service imports. It provides the cross-cutting infrastructure that would otherwise be duplicated across services: configuration, database sessions, authentication, caching, structured logging, event publishing, and the exception hierarchy.

No business logic lives here. If you find yourself adding domain rules to `shared`, they belong in a service instead.

## Package layout

| Sub-package | Responsibility |
|-------------|---------------|
| `shared.config` | Pydantic BaseSettings — single source of truth for env vars |
| `shared.database` | Async SQLAlchemy engines, `get_db` / `get_read_db` generators, `Base` |
| `shared.auth` | Token verification, `TenantContext`, `require_scope` |
| `shared.cache` | Singleton `redis.asyncio.Redis` client |
| `shared.messaging` | Transactional outbox — event queuing inside a DB transaction |
| `shared.exceptions` | `FileNestError` hierarchy — all domain errors |
| `shared.logging` | structlog setup (`configure_logging`, `get_logger`) |
| `shared.telemetry` | OpenTelemetry initialisation (Phase 6) |

## Installation

`shared` is a uv workspace member. It is listed as a dependency in each service's `pyproject.toml`:

```toml
# services/file/pyproject.toml
dependencies = ["filenest-shared", ...]
```

After `uv sync` at the repo root, all services can import from `shared.*`.

## Key rules

- Every service's `lifespan` startup must call `configure_logging()` and `close_redis()` on shutdown.
- Never import from `shared.database.session` directly — always use `shared.database` (the package `__init__`).
- Never construct `Settings()` yourself — import the singleton `settings` from `shared.config`.
