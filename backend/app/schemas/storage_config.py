"""app.schemas.storage_config — Pydantic request/response models for storage configuration."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StorageConfigUpdateRequest(BaseModel):
    """
    Body for updating BYOB storage credentials.

    Sensitive fields (access_key_id, secret_access_key, kms_key_id) are
    encrypted before persistence. Plaintext routing fields (bucket_name,
    region, endpoint_url) are stored as-is for display and provider init.

    endpoint_url is required for minio, r2, and rustfs; leave null for s3,
    azure_blob, and gcs which use standard SDK endpoints.
    """

    bucket_name: str = Field(..., min_length=1, max_length=255)
    region: str | None = Field(default=None, max_length=100)
    endpoint_url: str | None = Field(default=None, description="Required for MinIO, R2, and RustFS.")
    access_key_id: str = Field(..., min_length=1)
    secret_access_key: str = Field(..., min_length=1)
    server_side_encryption: Literal["AES256", "aws:kms"] = "AES256"
    kms_key_id: str | None = Field(default=None, description="Only used when server_side_encryption is aws:kms.")


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
