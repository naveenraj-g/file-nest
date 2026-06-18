"""app.models.project — SQLAlchemy ORM model for the projects table."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from app.core.database import Base


class Project(Base):
    """
    A project belongs to one organisation and is the unit of storage/processing config.

    The organization_id is a string FK to the IAM's BetterAuth organisation — no
    cross-DB join is needed because the IAM is the source of truth for org identity.
    """

    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    storage_mode = Column(String(20), nullable=False, default="managed")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
