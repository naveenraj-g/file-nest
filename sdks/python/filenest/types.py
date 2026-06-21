"""
filenest.types — Pydantic v2 models for all FileNest API responses.

All SDK methods return instances of these models. Use .model_dump() or
.model_dump_json() to serialize.

Usage:
    from filenest.types import File, FileStatus, SearchResults
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class FileStatus(StrEnum):
    """All possible states a file can be in."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    DELETED = "deleted"


class File(BaseModel):
    """A file stored in a FileNest project."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    project_id: str = Field(alias="projectId")
    organization_id: str = Field(alias="organizationId")
    filename: str
    mime_type: str = Field(alias="mimeType")
    size: int
    status: FileStatus
    storage_key: str = Field(alias="storageKey")
    folder_id: str | None = Field(None, alias="folderId")
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    version_count: int = Field(1, alias="versionCount")
    deleted_at: datetime | None = Field(None, alias="deletedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class FileVersion(BaseModel):
    """A historical version of a file."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    file_id: str = Field(alias="fileId")
    version_number: int = Field(alias="versionNumber")
    size: int
    storage_key: str = Field(alias="storageKey")
    change_note: str | None = Field(None, alias="changeNote")
    created_at: datetime = Field(alias="createdAt")


class Folder(BaseModel):
    """A folder in a FileNest project."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    project_id: str = Field(alias="projectId")
    parent_folder_id: str | None = Field(None, alias="parentFolderId")
    name: str
    path: str
    file_count: int | None = Field(None, alias="fileCount")
    total_size_bytes: int | None = Field(None, alias="totalSizeBytes")
    created_at: datetime = Field(alias="createdAt")


class Webhook(BaseModel):
    """A configured webhook endpoint."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    project_id: str = Field(alias="projectId")
    name: str
    url: str
    events: list[str]
    status: str
    signing_secret: str = Field(alias="signingSecret")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class Pagination(BaseModel):
    """Pagination metadata attached to list responses."""
    total: int
    limit: int
    offset: int
    has_more: bool = Field(alias="hasMore")


class ListResponse(BaseModel, Generic[T]):
    """Paginated list response wrapper."""
    data: list[T]
    pagination: Pagination


class MetadataFilter(BaseModel):
    """Key-value metadata filter for search queries."""
    model_config = ConfigDict(extra="allow")

    # Extra fields are passed as metadata key-value pairs.
    # e.g. MetadataFilter(patientId="P-12345", documentType="LabReport")


class SearchFilters(BaseModel):
    """Filters for search queries."""
    metadata: MetadataFilter | None = None
    tags: list[str] | None = None
    mime_type: list[str] | None = Field(None, alias="mimeType")
    created_after: datetime | None = Field(None, alias="createdAfter")
    created_before: datetime | None = Field(None, alias="createdBefore")
    folder_id: str | None = Field(None, alias="folderId")
    size_min: int | None = Field(None, alias="sizeMin")
    size_max: int | None = Field(None, alias="sizeMax")


class SearchHit(BaseModel):
    """A single search result with relevance score and highlights."""
    model_config = ConfigDict(populate_by_name=True)

    file_id: str = Field(alias="fileId")
    filename: str
    score: float
    highlights: dict[str, list[str]] = Field(default_factory=dict)
    file: File


class SearchResults(BaseModel):
    """Full search response including hits, total count, and facets."""
    hits: list[SearchHit]
    total: int
    query_time_ms: int = Field(alias="queryTimeMs")
    facets: dict[str, list[dict]] | None = None


class UploadToken(BaseModel):
    """Short-lived upload token for browser-side uploads."""
    model_config = ConfigDict(populate_by_name=True)

    token: str
    expires_at: datetime = Field(alias="expiresAt")
    constraints: dict[str, Any] = Field(default_factory=dict)


class DownloadUrlResponse(BaseModel):
    """Presigned download URL response."""
    model_config = ConfigDict(populate_by_name=True)

    url: str
    expires_at: datetime = Field(alias="expiresAt")
    filename: str
