"""
shared.database — Public API for database session management.

Re-exports the declarative Base (used by all ORM models) and the two
session-factory dependencies for use with FastAPI's dependency injection.

Usage:
    from shared.database import Base, get_db, get_read_db
"""
from .session import AsyncSessionLocal, Base, get_db, get_read_db

__all__ = ["Base", "get_db", "get_read_db", "AsyncSessionLocal"]
