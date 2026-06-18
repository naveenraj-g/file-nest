"""
shared.models — SQLAlchemy ORM models for the FileNest backend.

All models inherit from the shared `Base` so Alembic autogenerate can discover
the full schema in a single pass. Import from this package rather than from
individual model modules to ensure all models are registered before Alembic runs.

Usage:
    from shared.models import Project
"""
from .project import Project

__all__ = ["Project"]
