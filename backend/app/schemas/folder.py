"""
app.schemas.folder — Pydantic request/response models for folders and file move.

Usage:
    from app.schemas.folder import FolderCreateRequest, FolderResponse
"""
from datetime import datetime

from pydantic import BaseModel, field_validator


class FolderCreateRequest(BaseModel):
    """Body for creating a new folder."""
    name: str
    parent_folder_id: str | None = None

    @field_validator("name")
    @classmethod
    def name_no_slash(cls, v: str) -> str:
        """Folder names must not contain slashes — slashes are path separators."""
        v = v.strip()
        if not v:
            raise ValueError("Folder name must not be empty")
        if "/" in v:
            raise ValueError("Folder name must not contain '/'")
        return v


class FolderResponse(BaseModel):
    """A single folder record."""
    id: str
    organization_id: str
    project_id: str
    parent_folder_id: str | None
    name: str
    path: str
    created_at: datetime


class FolderListResponse(BaseModel):
    """All folders in a project."""
    items: list[FolderResponse]
    total: int


class DeleteFolderResponse(BaseModel):
    """Returned after a successful folder soft-delete."""
    id: str
    deleted: bool = True
