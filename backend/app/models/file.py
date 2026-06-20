"""app.models.file — SQLAlchemy ORM model for the files table."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class File(Base):
    """
    A file record — metadata only. Actual bytes live in object storage (storage_key).

    The status column drives the file lifecycle:
      pending → uploading → ready | failed | quarantined
    """

    __tablename__ = "files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
    storage_key = Column(String, nullable=True)     # set after upload confirmed
    folder_id = Column(String, nullable=True)
    # Classification result set by ClassificationStage: document, image, video, audio, archive, other
    category = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
