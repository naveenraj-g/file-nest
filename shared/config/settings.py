"""
shared.config.settings — Application-wide configuration via Pydantic BaseSettings.

Reads environment variables and an optional .env file (loaded automatically when
dotenv-load is set). All services import the singleton `settings` object rather
than constructing their own Settings instance — this guarantees a single source
of truth and avoids repeated env-var parsing.

Usage:
    from shared.config import settings

    url = settings.database_primary_url
    if settings.is_dev:
        ...
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Single configuration object for the entire FileNest backend.

    Values are read from environment variables first, then .env in the current
    working directory. Fields marked with `alias` use the UPPER_SNAKE_CASE env
    var name; all others match the field name by default (case-insensitive).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Runtime environment ────────────────────────────────────────────────────
    env: str = "development"
    service_name: str = "filenest"

    # ── Database ───────────────────────────────────────────────────────────────
    # Primary accepts writes; replica is used for read-heavy queries via get_read_db.
    database_primary_url: str = Field(..., alias="DATABASE_PRIMARY_URL")
    database_replica_url: str | None = Field(None, alias="DATABASE_REPLICA_URL")
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_cluster_mode: bool = False

    # ── NATS ───────────────────────────────────────────────────────────────────
    nats_url: str = "nats://localhost:4222"
    nats_stream_name: str = "FILENEST_EVENTS"

    # ── Storage ────────────────────────────────────────────────────────────────
    # Provider type controls which StorageProvider implementation is used:
    #   "s3" — covers AWS S3, RustFS, MinIO, Cloudflare R2 (all S3-compatible)
    #   "azure" — Azure Blob Storage (Phase 7)
    #   "gcs"   — Google Cloud Storage (Phase 7)
    default_storage_provider: str = "s3"

    # S3-compatible settings (used when default_storage_provider == "s3")
    s3_endpoint_url: str | None = None       # None → real AWS S3; set URL for RustFS/MinIO/R2
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket_name: str = "filenest"
    s3_region: str = "us-east-1"
    # Path-style access is required for RustFS, MinIO, and Cloudflare R2.
    # Set to False when using AWS S3 virtual-hosted-style URLs in production.
    s3_force_path_style: bool = True

    # Optional server-side envelope encryption key (32-byte base64-encoded AES-256).
    storage_encryption_key: str | None = None

    # ── Security ───────────────────────────────────────────────────────────────
    jwt_secret_key: str = "dev-secret"       # Must be overridden in production
    api_key_salt: str = "dev-salt"

    # ── Upload thresholds ──────────────────────────────────────────────────────
    # Files larger than this threshold are handled as multipart uploads (Phase 2).
    multipart_threshold_bytes: int = 104857600  # 100 MB

    # ── Feature flags ──────────────────────────────────────────────────────────
    healthcare_pack_enabled: bool = False

    # ── Observability ──────────────────────────────────────────────────────────
    otel_endpoint: str | None = None

    @property
    def is_dev(self) -> bool:
        """Return True when running in the local development environment."""
        return self.env == "development"


settings = Settings()
