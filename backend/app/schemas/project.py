"""app.schemas.project — Pydantic request/response models for projects."""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")[:100]


class CreateProjectRequest(BaseModel):
    """Body for creating a new project."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, description="Auto-derived from name if omitted.")
    description: str | None = None
    storage_mode: Literal["managed", "byob"] = "managed"
    storage_provider: Literal["s3", "azure_blob", "gcs", "minio", "r2", "restfs"] = "s3"

    @field_validator("slug", mode="before")
    @classmethod
    def validate_slug(cls, v: str | None, info) -> str:
        if v is None:
            name = info.data.get("name", "")
            return _slugify(name)
        slug = v.lower().strip()
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,98}[a-z0-9]$|^[a-z0-9]$", slug):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens, 1–100 chars")
        return slug


class UpdateProjectRequest(BaseModel):
    """Body for updating mutable project fields. All fields are optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    versioning_enabled: bool | None = None
    ocr_enabled: bool | None = None


class ProjectResponse(BaseModel):
    """Full project representation."""

    id: str
    organization_id: str
    name: str
    slug: str
    description: str | None
    storage_mode: str
    storage_provider: str
    versioning_enabled: bool
    ocr_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    items: list[ProjectResponse]
    total: int
