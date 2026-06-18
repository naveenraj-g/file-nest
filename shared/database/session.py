"""
shared.database.session — Async SQLAlchemy engine and session factories.

Provides two session generators:
  - `get_db`      → primary engine (reads + writes)
  - `get_read_db` → replica engine (read-only queries)

Both are intended for use as FastAPI dependencies via `Depends(get_db)`.
The session is yielded inside an `async with` block, so the connection is
returned to the pool automatically when the request finishes — services should
call `db.flush()` to get DB-assigned IDs but must NOT call `db.commit()`;
the context manager commits on clean exit and rolls back on exception.

The SQLAlchemy `Base` class is exported here so that all ORM models in
`services/*/repository.py` inherit from the same metadata object, which
Alembic's env.py uses for autogenerate.

Usage:
    from shared.database import get_db, Base
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession

    async def my_endpoint(db: AsyncSession = Depends(get_db)):
        ...
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from shared.config import settings

# ── Engine setup ───────────────────────────────────────────────────────────────

_primary_engine = create_async_engine(
    settings.database_primary_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.is_dev,   # SQL statement logging in dev only
)

# Fall back to primary when no replica URL is configured (local dev / tests)
_replica_url = settings.database_replica_url or settings.database_primary_url
_replica_engine = create_async_engine(
    _replica_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(_primary_engine, expire_on_commit=False)
AsyncReadSessionLocal = async_sessionmaker(_replica_engine, expire_on_commit=False)


# ── Base class shared by all ORM models ───────────────────────────────────────

class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.

    All models across every service must inherit from this single Base so that
    Alembic's autogenerate can detect the full schema in one pass.
    """


# ── FastAPI dependency generators ─────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a primary-database session for use in FastAPI Depends().

    The session commits on clean exit and rolls back on any unhandled exception.
    Service and repository code must call `db.flush()` (not `db.commit()`) to
    retrieve DB-assigned IDs within a transaction.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a read-replica session for use in FastAPI Depends().

    Use this for list/search endpoints that do not need the latest committed
    write, to reduce load on the primary. Never use this session for writes.
    """
    async with AsyncReadSessionLocal() as session:
        yield session
