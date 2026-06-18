"""app.schemas.file — Pydantic request/response models for files."""
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FileStatus(StrEnum):
    """File lifecycle states."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class UploadInitRequest(BaseModel):
    """Body for initiating a file upload."""
    filename: str
    content_type: str
    size_bytes: int
    folder_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class UploadInitResponse(BaseModel):
    """Returned after upload initiation. Client PUTs bytes to upload_url."""
    file_id: str
    upload_url: str
    upload_id: str | None = None  # multipart only (Phase 2)
    expires_at: datetime


class FileResponse(BaseModel):
    """Full file metadata record."""
    id: str
    organization_id: str
    project_id: str
    filename: str
    content_type: str
    size_bytes: int
    status: FileStatus
    storage_key: str
    folder_id: str | None
    metadata: dict[str, str]
    created_at: datetime
    updated_at: datetime


class FileListResponse(BaseModel):
    """Cursor-paginated list of files."""
    items: list[FileResponse]
    total: int
    cursor: str | None = None


class DownloadUrlResponse(BaseModel):
    """Presigned download URL."""
    url: str
    expires_at: datetime


class ConfirmUploadResponse(BaseModel):
    """Returned after the client confirms a completed upload."""
    id: str
    status: FileStatus


class DeleteResponse(BaseModel):
    """Returned after a successful soft delete."""
    id: str
    deleted: bool = True
