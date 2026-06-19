"""app.schemas.storage_config — Pydantic request/response models for storage configuration."""
from datetime import datetime

from pydantic import BaseModel, Field


class StorageConfigResponse(BaseModel):
    """
    Non-sensitive storage configuration for a project.

    Encrypted credentials are never returned — only plaintext routing fields.
    """

    project_id: str
    environment: str
    storage_mode: str
    provider: str
    region: str | None
    bucket_name: str | None
    endpoint_url: str | None
    server_side_encryption: str
    status: str
    last_verified_at: datetime | None


class StorageVerifyResponse(BaseModel):
    """Result of a storage connectivity probe (write + delete a test object)."""

    ok: bool
    latency_ms: float | None = None
    error: str | None = None
