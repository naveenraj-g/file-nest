"""
app.schemas.upload_token — Pydantic request/response models for upload tokens.

CreateUploadTokenRequest fields use snake_case to match what the Node SDK sends.
UploadTokenResponse mirrors the UploadToken TypeScript interface in @filenest/core
after the HTTP client's camelizeKeys transformer is applied.

Usage:
    from app.schemas.upload_token import CreateUploadTokenRequest, UploadTokenResponse
"""
from datetime import datetime

from pydantic import BaseModel, Field


class CreateUploadTokenRequest(BaseModel):
    """Body for POST /v1/projects/{project_id}/upload-tokens."""

    max_size: int | None = Field(None, description="Maximum file size in bytes.")
    allowed_mime_types: list[str] | None = Field(None, description="MIME patterns, e.g. ['image/*'].")
    max_files: int | None = Field(None, description="Maximum number of files per token.")
    folder_id: str | None = Field(None, description="Default target folder for uploads using this token.")
    metadata: dict | None = Field(None, description="Default metadata applied to every upload.")
    expires_in: int = Field(3600, ge=60, le=86400, description="Token TTL in seconds (60–86400).")


class UploadTokenConstraints(BaseModel):
    """Constraints embedded in the token response, surfaced to the browser."""

    max_size: int
    allowed_mime_types: list[str]
    max_files: int


class UploadTokenResponse(BaseModel):
    """Response body for POST /v1/projects/{project_id}/upload-tokens."""

    token: str
    expires_at: datetime
    constraints: UploadTokenConstraints
