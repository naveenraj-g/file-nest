"""
app.core.database — Async SQLAlchemy engine, session factories, and Base.

Provides:
  - Base          — declarative base shared by all ORM models
  - get_db        — primary session dependency (writes + reads)
  - get_read_db   — replica session dependency (read-only)

Both dependencies yield sessions that auto-commit on clean exit and roll back on
exception. Service/repository code must call `session.flush()` (not `session.commit()`)
to get DB-assigned IDs within a transaction.

Usage:
    from app.core.database import get_db, Base
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""


_primary_engine = create_async_engine(
    settings.database_primary_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.is_dev,
)

_replica_url = settings.database_replica_url or settings.database_primary_url
_replica_engine = create_async_engine(
    _replica_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(_primary_engine, expire_on_commit=False)
AsyncReadSessionLocal = async_sessionmaker(_replica_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a primary-database session. Commits on clean exit, rolls back on exception."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a read-replica session. Use for list/search endpoints, never for writes."""
    async with AsyncReadSessionLocal() as session:
        yield session
