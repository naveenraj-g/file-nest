"""
services.identity.schemas — Pydantic request/response models for the Identity Service.

These are the public API contract types for API key management. They are separate
from the SQLAlchemy ORM model in shared/models/api_key.py — never return ORM
objects directly from routes.

Usage:
    from services.identity.schemas import CreateApiKeyRequest, ApiKeyResponse
"""
from datetime import datetime

from pydantic import BaseModel, Field

ALL_SCOPES = [
    "files:upload",
    "files:download",
    "files:read",
    "files:delete",
    "files:update_metadata",
    "api_keys:create",
    "api_keys:revoke",
    "projects:read",
    "projects:update",
    "audit:read",
    "compliance:manage",
]


class CreateApiKeyRequest(BaseModel):
    """Body sent by the client to create a new API key."""

    name: str = Field(..., min_length=1, max_length=255, description="Human-readable key name")
    scopes: list[str] = Field(
        default=ALL_SCOPES,
        description="Permission scopes granted to this key. Defaults to all scopes.",
    )
    test_mode: bool = Field(
        default=False,
        description="If true, creates a fn_test_ prefixed key for non-production use.",
    )
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="Key TTL in days. Omit for a non-expiring key.",
    )


class ApiKeyResponse(BaseModel):
    """
    Representation of an API key returned by GET and DELETE endpoints.

    The `key` field (raw value) is ONLY populated on the create response.
    All subsequent reads return null for `key` — it cannot be recovered.
    """

    id: str
    name: str
    key_prefix: str
    key: str | None = Field(
        default=None,
        description="Raw key — set once on creation, null thereafter.",
    )
    scopes: list[str]
    is_test_mode: bool
    is_revoked: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    """Paginated list of API keys for the current project."""

    items: list[ApiKeyResponse]
    total: int
