"""
shared.models.project — SQLAlchemy ORM model for the `projects` table.

A project is the primary unit of configuration in FileNest. Files, API keys,
webhooks, and compliance settings all belong to a project. Projects belong to
an organisation stored in the IAM database — the `organization_id` column is
the cross-DB foreign key that links them.

Storage mode controls where file bytes are sent:
  - "managed" — FileNest platform bucket (default, zero customer config)
  - "byob"    — customer-supplied endpoint + encrypted credentials (Phase 7)

Usage:
    from shared.models.project import Project
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from shared.database import Base


class Project(Base):
    """
    ORM model for the `projects` table.

    Created via the Project Service (`services/project/`). Every subsequent
    FileNest operation (upload, download, search) is scoped to a single project.

    Attributes:
        id:              UUID primary key.
        organization_id: IAM organisation UUID — cross-DB FK, no relational join.
        name:            Human-readable project name.
        slug:            URL-safe identifier, unique within an organisation.
        description:     Optional free-text description.
        storage_mode:    "managed" (platform bucket) or "byob" (Phase 7).
        is_active:       Soft-disable flag; inactive projects reject uploads.
        created_at:      Creation timestamp.
        updated_at:      Last mutation timestamp.
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
