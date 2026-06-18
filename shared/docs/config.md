# shared.config — Configuration Reference

## Purpose

Provides a single `Settings` object (Pydantic `BaseSettings`) that reads every environment variable the backend needs. All services import the pre-constructed singleton `settings` — constructing your own `Settings()` is not allowed.

## Usage

```python
from shared.config import settings

# Read a value
url = settings.database_primary_url

# Check environment
if settings.is_dev:
    print("running locally")
```

## Environment variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENV` | str | `development` | Runtime environment (`development`, `production`) |
| `SERVICE_NAME` | str | `filenest` | Injected into log entries and OTEL spans |
| `DATABASE_PRIMARY_URL` | str | **required** | asyncpg connection URL for the primary DB |
| `DATABASE_REPLICA_URL` | str | same as primary | asyncpg URL for the read replica |
| `DATABASE_POOL_SIZE` | int | `20` | SQLAlchemy pool size per process |
| `DATABASE_MAX_OVERFLOW` | int | `10` | Extra connections above pool_size |
| `REDIS_URL` | str | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_CLUSTER_MODE` | bool | `false` | Set `true` for Redis Cluster |
| `NATS_URL` | str | `nats://localhost:4222` | NATS server URL |
| `NATS_STREAM_NAME` | str | `FILENEST_EVENTS` | JetStream stream name |
| `DEFAULT_STORAGE_PROVIDER` | str | `s3` | Default provider when project has none configured |
| `S3_ENDPOINT_URL` | str | `None` | Override S3 endpoint (set to MinIO URL in dev) |
| `S3_ACCESS_KEY_ID` | str | `None` | S3 / MinIO access key |
| `S3_SECRET_ACCESS_KEY` | str | `None` | S3 / MinIO secret key |
| `S3_BUCKET_NAME` | str | `filenest` | Default bucket |
| `S3_REGION` | str | `us-east-1` | S3 region |
| `S3_FORCE_PATH_STYLE` | bool | `true` | Required for RustFS, MinIO, and Cloudflare R2; set `false` for AWS S3 virtual-hosted-style |
| `STORAGE_ENCRYPTION_KEY` | str | `None` | 32-byte AES-256 key (base64) for server-side encryption |
| `JWT_SECRET_KEY` | str | `dev-secret` | HMAC key for signing JWTs — **must override in production** |
| `API_KEY_SALT` | str | `dev-salt` | Salt for hashing API keys — **must override in production** |
| `MULTIPART_THRESHOLD_BYTES` | int | `104857600` | Files larger than this use multipart upload (100 MB) |
| `HEALTHCARE_PACK_ENABLED` | bool | `false` | Enables HIPAA/FHIR/PHI features |
| `OTEL_ENDPOINT` | str | `None` | OpenTelemetry collector gRPC endpoint |

## Local dev defaults

Copy `.env.example` to `.env` at the repo root. The example file pre-fills all values for the `docker compose` stack (RustFS at `localhost:9000`, PostgreSQL at `localhost:5432`, etc.).

## Properties

`settings.is_dev` — returns `True` when `ENV == "development"`. Used by logging (console vs JSON) and SQLAlchemy (echo SQL vs not).
