"""app.schemas.file — Pydantic request/response models for files and file versions."""
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


class FileVersionResponse(BaseModel):
    """Metadata for a single file version snapshot."""
    id: str
    file_id: str
    version_number: int
    storage_key: str
    size_bytes: int
    content_type: str
    created_at: datetime


class FileVersionListResponse(BaseModel):
    """All version snapshots for a file, newest first."""
    items: list[FileVersionResponse]
    total: int


class RestoreVersionResponse(BaseModel):
    """Returned after a version is restored as the current file state."""
    file_id: str
    version_number: int  # the new current version number after restore


# ── Multipart upload ────────────────────────────────────────────────────────

class MultipartStartRequest(BaseModel):
    """Body for initiating a multipart upload."""
    filename: str
    content_type: str
    total_size_bytes: int
    folder_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class MultipartStartResponse(BaseModel):
    """Returned after multipart upload is initiated."""
    upload_id: str
    file_id: str


class MultipartPartUrlResponse(BaseModel):
    """Presigned URL for a single part upload."""
    upload_id: str
    part_number: int
    url: str
    expires_at: datetime


class MultipartPart(BaseModel):
    """A completed part descriptor sent by the client on complete."""
    part_number: int = Field(alias="PartNumber")
    etag: str = Field(alias="ETag")

    model_config = {"populate_by_name": True}


class MultipartCompleteRequest(BaseModel):
    """Body for completing a multipart upload."""
    parts: list[MultipartPart]


class MultipartCompleteResponse(BaseModel):
    """Returned after multipart upload is assembled."""
    file_id: str
    status: FileStatus


class MultipartAbortResponse(BaseModel):
    """Returned after a multipart upload is aborted."""
    upload_id: str
    aborted: bool = True
