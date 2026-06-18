"""
app.core.config — Application-wide configuration via Pydantic Settings.

All runtime settings are read from environment variables and an optional .env
file. Import the `settings` singleton everywhere; never instantiate Settings
more than once.

Usage:
    from app.core.config import settings

    url = settings.database_primary_url
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single configuration object for the entire FileNest backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Runtime ───────────────────────────────────────────────────────────────
    env: str = "development"
    service_name: str = "filenest"

    # ── Database ──────────────────────────────────────────────────────────────
    database_primary_url: str = Field(..., alias="DATABASE_PRIMARY_URL")
    database_replica_url: str | None = Field(None, alias="DATABASE_REPLICA_URL")
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── NATS ──────────────────────────────────────────────────────────────────
    nats_url: str = "nats://localhost:4222"
    nats_stream_name: str = "FILENEST_EVENTS"

    # ── IAM ───────────────────────────────────────────────────────────────────
    # URL of the BetterAuth IAM. Used to verify fn_ API keys and JWKS endpoint.
    iam_url: str = Field("http://localhost:3000", alias="IAM_URL")

    # ── Storage ───────────────────────────────────────────────────────────────
    default_storage_provider: str = "s3"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket_name: str = "filenest"
    s3_region: str = "us-east-1"
    s3_force_path_style: bool = True
    storage_encryption_key: str | None = None

    # ── Security ──────────────────────────────────────────────────────────────
    # Used only for HS256 local JWT testing. Production uses JWKS from IAM.
    jwt_secret_key: str = "dev-secret"

    # ── Upload ────────────────────────────────────────────────────────────────
    multipart_threshold_bytes: int = 104857600  # 100 MB

    # ── Feature flags ─────────────────────────────────────────────────────────
    healthcare_pack_enabled: bool = False

    # ── Observability ─────────────────────────────────────────────────────────
    otel_endpoint: str | None = None

    @property
    def is_dev(self) -> bool:
        """True when running in the local development environment."""
        return self.env == "development"

    @property
    def iam_jwks_url(self) -> str:
        """JWKS endpoint on the IAM for RS256 JWT verification."""
        return f"{self.iam_url}/api/auth/jwks"


settings = Settings()
