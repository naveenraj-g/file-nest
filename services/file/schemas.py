"""
services.file.schemas — Pydantic request/response models for the File Service.

These are the public API contract types. They are intentionally separate from
the SQLAlchemy ORM models in repository.py — never mix the two or return ORM
objects directly from routes.

FastAPI uses these schemas to:
  - Parse and validate incoming request bodies
  - Generate the OpenAPI schema at /docs (auto-generated — do not duplicate there)
  - Serialise outgoing responses

Usage:
    from services.file.schemas import UploadInitRequest, FileResponse
"""
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FileStatus(StrEnum):
    """Lifecycle states a file moves through from upload initiation to availability."""

    PENDING = "pending"           # Record created; upload not yet confirmed
    PROCESSING = "processing"     # Virus scan / MIME validation in progress
    READY = "ready"               # Available for download
    FAILED = "failed"             # Processing failed; file may be missing
    QUARANTINED = "quarantined"   # Virus detected; access blocked


class UploadInitRequest(BaseModel):
    """
    Body sent by the client to initiate a single-file upload.

    The client receives back a presigned upload URL; it then PUTs the file
    bytes directly to that URL (MinIO / S3) without routing through this service.
    """

    filename: str
    content_type: str
    size_bytes: int
    folder_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class UploadInitResponse(BaseModel):
    """
    Returned after a successful upload initiation.

    The client uses `upload_url` to PUT the file bytes. For files exceeding
    `MULTIPART_THRESHOLD_BYTES`, `upload_id` will be set and the client
    must use the multipart protocol (Phase 2).
    """

    file_id: str
    upload_url: str
    upload_id: str | None = None   # Non-null only for multipart uploads (Phase 2)
    expires_at: datetime


class FileResponse(BaseModel):
    """Full representation of a file record, returned by GET /files/{file_id}."""

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
    """Paginated list of files. Use `cursor` as the `cursor` query param for the next page."""

    items: list[FileResponse]
    total: int
    cursor: str | None = None   # None means this is the last page


class DownloadUrlResponse(BaseModel):
    """Presigned download URL returned by GET /files/{id}/download."""

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
