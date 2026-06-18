"""
services.project.schemas — Pydantic request/response models for the Project Service.

These are the public API contract types for project management. Separate from
the ORM model in shared/models/project.py — never return ORM objects from routes.

Usage:
    from services.project.schemas import CreateProjectRequest, ProjectResponse
"""
import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")[:100]


class CreateProjectRequest(BaseModel):
    """Body sent by the client to create a new project."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(
        default=None,
        description="URL-safe identifier. Auto-derived from name if omitted.",
    )
    description: str | None = None

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


class ProjectResponse(BaseModel):
    """Full representation of a project, returned by GET and POST endpoints."""

    id: str
    organization_id: str
    name: str
    slug: str
    description: str | None
    storage_mode: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """List of projects belonging to the caller's organisation."""

    items: list[ProjectResponse]
    total: int
