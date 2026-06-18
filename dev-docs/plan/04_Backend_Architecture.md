# FileNest v1.0 — Backend Architecture

**Version:** 1.0.0
**Status:** Approved for Engineering
**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.x · Pydantic v2
**Last Updated:** 2026-06-15

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Shared Infrastructure](#2-shared-infrastructure)
3. [Identity Service](#3-identity-service)
4. [Project Service](#4-project-service)
5. [File Service](#5-file-service)
6. [Storage Service](#6-storage-service)
7. [Metadata Service](#7-metadata-service)
8. [Search Service](#8-search-service)
9. [Processing Service](#9-processing-service)
10. [Audit Service](#10-audit-service)
11. [Webhook Service](#11-webhook-service)
12. [Compliance Service](#12-compliance-service)
13. [Healthcare Service](#13-healthcare-service)
14. [Inter-Service Communication](#14-inter-service-communication)
15. [Error Handling](#15-error-handling)
16. [Observability](#16-observability)

---

## 1. Project Structure

### 1.1 Monorepo Layout

```
filenest/
├── services/
│   ├── identity/
│   ├── project/
│   ├── file/
│   ├── storage/
│   ├── metadata/
│   ├── search/
│   ├── processing/
│   ├── audit/
│   ├── webhook/
│   ├── compliance/
│   └── healthcare/
├── shared/
│   ├── models/          # SQLAlchemy models (shared)
│   ├── schemas/         # Pydantic schemas (shared)
│   ├── database/        # DB session, migrations
│   ├── cache/           # Redis client
│   ├── messaging/       # NATS client
│   ├── auth/            # Auth middleware
│   ├── config/          # Settings
│   ├── exceptions/      # Common exceptions
│   ├── logging/         # Structured logging
│   └── telemetry/       # OpenTelemetry setup
├── migrations/
│   └── alembic/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
├── helm/
└── scripts/
```

### 1.2 Service Internal Structure

Each service follows the same internal layout:

```
services/file/
├── main.py              # FastAPI app factory
├── router.py            # Route registration
├── routes/
│   ├── upload.py
│   ├── download.py
│   ├── versions.py
│   └── folders.py
├── service.py           # Business logic layer
├── repository.py        # Database access layer
├── schemas.py           # Request/response Pydantic models
├── dependencies.py      # FastAPI dependency injection
├── events.py            # Event publishers
└── tests/
```

### 1.3 Application Factory Pattern

```python
# services/file/main.py
from fastapi import FastAPI
from shared.database import init_db
from shared.cache import init_redis
from shared.messaging import init_nats
from shared.telemetry import init_telemetry
from shared.logging import setup_logging
from .router import router
from .middleware import TenantContextMiddleware, RequestIDMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="FileNest File Service",
        version="1.0.0",
        docs_url="/docs" if settings.env != "production" else None,
    )

    # Middleware (order matters — outermost first)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TenantContextMiddleware)

    # Routers
    app.include_router(router, prefix="/v1")

    # Lifecycle
    @app.on_event("startup")
    async def startup():
        await init_db()
        await init_redis()
        await init_nats()
        init_telemetry(service_name="file-service")
        setup_logging(service_name="file-service")

    return app
```

### 1.4 Settings Pattern

```python
# shared/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Environment
    env: str = "development"
    service_name: str = "filenest"

    # Database
    database_primary_url: str
    database_replica_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cluster_mode: bool = False

    # NATS
    nats_url: str = "nats://localhost:4222"
    nats_stream_name: str = "FILENEST_EVENTS"

    # Storage
    default_storage_provider: str = "s3"
    storage_encryption_key: str  # AES-256 key for BYOB config encryption

    # Security
    jwt_secret_key: str
    api_key_salt: str

    # Feature flags
    healthcare_pack_enabled: bool = True

settings = Settings()
```

---

## 2. Shared Infrastructure

### 2.1 Database Session Management

```python
# shared/database/session.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager

engine = create_async_engine(
    settings.database_primary_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    echo=settings.env == "development",
)

read_engine = create_async_engine(
    settings.database_replica_url,
    pool_size=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
ReadAsyncSessionLocal = async_sessionmaker(read_engine, expire_on_commit=False)

@asynccontextmanager
async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# FastAPI dependency
async def get_db() -> AsyncSession:
    async with get_db_session() as session:
        yield session
```

### 2.2 Auth Middleware

```python
# shared/auth/middleware.py
from fastapi import Request, HTTPException
from shared.cache import redis_client
from shared.models import APIKey, ServiceAccount

class AuthContext:
    organization_id: str
    project_id: str
    actor_type: str  # 'api_key' | 'service_account'
    actor_id: str
    scopes: list[str]

async def authenticate_request(request: Request) -> AuthContext:
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ")

    # Try cache first
    cache_key = f"auth:{hash_token(token)}"
    cached = await redis_client.get(cache_key)
    if cached:
        return AuthContext.model_validate_json(cached)

    # Validate token type
    if token.startswith("fn_live_") or token.startswith("fn_test_"):
        ctx = await validate_api_key(token)
    elif token.startswith("fn_sa_"):
        ctx = await validate_service_account(token)
    else:
        raise HTTPException(status_code=401, detail="Invalid token format")

    # Cache for 10 minutes
    await redis_client.setex(cache_key, 600, ctx.model_dump_json())
    return ctx

async def validate_api_key(token: str) -> AuthContext:
    key_hash = hash_api_key(token)
    api_key = await db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.status == "active",
    ).first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key expired")

    # Update usage stats (async, fire-and-forget)
    asyncio.create_task(update_key_usage(api_key.id))

    return AuthContext(
        organization_id=str(api_key.organization_id),
        project_id=str(api_key.project_id),
        actor_type="api_key",
        actor_id=str(api_key.id),
        scopes=api_key.scopes,
    )
```

### 2.3 Tenant Context

```python
# shared/auth/tenant.py
from contextvars import ContextVar

_tenant_ctx: ContextVar[AuthContext] = ContextVar("tenant_ctx")

def set_tenant_context(ctx: AuthContext) -> None:
    _tenant_ctx.set(ctx)

def get_tenant_context() -> AuthContext:
    ctx = _tenant_ctx.get(None)
    if ctx is None:
        raise RuntimeError("Tenant context not set — missing auth middleware?")
    return ctx

# FastAPI dependency
async def require_auth(
    request: Request,
    auth: AuthContext = Depends(authenticate_request),
) -> AuthContext:
    set_tenant_context(auth)
    # Set PostgreSQL session variable for RLS
    await db.execute(
        text("SET app.current_organization_id = :org_id"),
        {"org_id": auth.organization_id}
    )
    return auth
```

### 2.4 Permission Checking

```python
# shared/auth/permissions.py
PERMISSION_MAP = {
    "files:upload":          ["editor", "manager", "admin"],
    "files:download":        ["viewer", "editor", "manager", "admin"],
    "files:delete":          ["editor", "manager", "admin"],
    "files:read":            ["viewer", "editor", "manager", "admin"],
    "files:update_metadata": ["editor", "manager", "admin"],
    "api_keys:create":       ["manager", "admin"],
    "api_keys:revoke":       ["admin"],
    "projects:read":         ["viewer", "editor", "manager", "admin"],
    "projects:update":       ["manager", "admin"],
    "audit:read":            ["auditor", "admin"],
    "compliance:manage":     ["admin"],
}

def require_scope(scope: str):
    async def check(auth: AuthContext = Depends(require_auth)):
        if scope not in auth.scopes and "*" not in auth.scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required scope: {scope}"
            )
        return auth
    return check
```

---

## 3. Identity Service

### 3.1 Responsibilities

- Organization CRUD
- User registration, login, profile
- Role assignment and revocation
- API key lifecycle (create, rotate, revoke)
- Service account lifecycle
- Session management
- SSO (SAML/OAuth) — v2

### 3.2 Key Endpoints

```
POST /v1/auth/organizations            # Create organization
POST /v1/auth/login                    # User login
POST /v1/auth/refresh                  # Refresh access token
POST /v1/auth/logout                   # Invalidate session

GET  /v1/organizations/{id}            # Get organization
PUT  /v1/organizations/{id}            # Update organization

GET  /v1/users                         # List users in org
POST /v1/users/invite                  # Invite user
PUT  /v1/users/{id}/roles              # Update roles

POST /v1/api-keys                      # Create API key
GET  /v1/api-keys                      # List API keys
POST /v1/api-keys/{id}/rotate          # Rotate key
DELETE /v1/api-keys/{id}               # Revoke key

POST /v1/service-accounts              # Create service account
POST /v1/service-accounts/{id}/rotate  # Rotate secret
```

### 3.3 API Key Generation

```python
# services/identity/service.py
import secrets
import hashlib
from shared.models import APIKey

class APIKeyService:
    def generate_api_key(self, environment: str) -> tuple[str, str]:
        """Returns (full_key, key_hash). Store only the hash."""
        prefix = "fn_live_" if environment == "production" else "fn_test_"
        random_part = secrets.token_urlsafe(32)
        full_key = f"{prefix}{random_part}"

        # bcrypt for storage
        key_hash = bcrypt.hashpw(full_key.encode(), bcrypt.gensalt(rounds=12)).decode()

        return full_key, key_hash

    async def create_api_key(
        self,
        project_id: str,
        name: str,
        scopes: list[str],
        expires_at: datetime | None,
        auth: AuthContext,
    ) -> APIKeyCreated:
        full_key, key_hash = self.generate_api_key(environment=auth.environment)

        api_key = APIKey(
            organization_id=auth.organization_id,
            project_id=project_id,
            key_id=f"fn_key_{secrets.token_hex(8)}",
            key_hash=key_hash,
            key_prefix=full_key[:12] + "...",
            name=name,
            scopes=scopes,
            expires_at=expires_at,
            created_by=auth.actor_id,
        )

        self.db.add(api_key)
        await self.db.flush()

        # Audit log
        await self.audit.log(
            event_type="api_key.created",
            subject_type="api_key",
            subject_id=api_key.id,
            payload={"name": name, "scopes": scopes},
            auth=auth,
        )

        # Return the full key ONCE — never retrievable again
        return APIKeyCreated(
            key_id=api_key.key_id,
            key=full_key,  # Only returned at creation
            name=name,
            prefix=api_key.key_prefix,
            scopes=scopes,
            expires_at=expires_at,
        )
```

---

## 4. Project Service

### 4.1 Responsibilities

- Project CRUD
- Project configuration management
- Configuration validation
- Compliance profile assignment
- Capability pack activation
- Metadata schema management
- Webhook management
- Environment management

### 4.2 Configuration Validation

```python
# services/project/config_validator.py
from pydantic import BaseModel, validator, Field

class StorageConfig(BaseModel):
    provider: Literal["s3", "azure_blob", "gcs", "minio", "r2"]
    region: str | None = None
    bucket_name: str | None = None
    byob: bool = False
    encryption: Literal["AES256", "aws:kms", "none"] = "AES256"
    kms_key_id: str | None = None

    @validator("kms_key_id")
    def kms_required_for_kms_encryption(cls, v, values):
        if values.get("encryption") == "aws:kms" and not v:
            raise ValueError("kms_key_id required when encryption=aws:kms")
        return v

class ComplianceConfig(BaseModel):
    profile: Literal["generic", "healthcare", "finance", "legal", "insurance", "custom"]
    hipaa_controls: bool = False
    phi_detection: bool = False
    pii_detection: bool = False
    audit_retention_years: int = Field(1, ge=1, le=10)
    legal_hold_enabled: bool = False
    worm: bool = False
    retention_days: int = Field(365, ge=1)
    immutable_audit: bool = False

    @validator("hipaa_controls")
    def hipaa_requires_healthcare_profile(cls, v, values):
        if v and values.get("profile") not in ("healthcare", "custom"):
            raise ValueError("hipaa_controls requires healthcare or custom profile")
        return v

class ProjectConfig(BaseModel):
    storage: StorageConfig
    compliance: ComplianceConfig
    processing: ProcessingConfig
    metadata: MetadataConfig
    security: SecurityConfig
    versioning: VersioningConfig
    retention: RetentionConfig
    search: SearchConfig
```

### 4.3 Capability Pack Activation

```python
# services/project/capability_packs.py
CAPABILITY_PACKS: dict[str, dict] = {
    "healthcare": {
        "compliance": {
            "profile": "healthcare",
            "hipaa_controls": True,
            "phi_detection": True,
            "audit_retention_years": 7,
            "legal_hold_enabled": True,
            "immutable_audit": True,
        },
        "processing": {
            "phi_detection": True,
            "ocr": True,
            "virus_scan": True,
            "classification": True,
        },
    },
    "finance": {
        "compliance": {
            "profile": "finance",
            "worm": True,
            "legal_hold_enabled": True,
            "retention_days": 2555,
            "audit_retention_years": 7,
        },
        "processing": {
            "pii_detection": True,
            "classification": True,
        },
    },
}

def apply_capability_pack(
    base_config: dict, pack_name: str, overrides: dict | None = None
) -> dict:
    pack = CAPABILITY_PACKS.get(pack_name)
    if not pack:
        raise ValueError(f"Unknown capability pack: {pack_name}")

    config = deep_merge(base_config, pack)
    if overrides:
        config = deep_merge(config, overrides)

    return config
```

---

## 5. File Service

### 5.1 Responsibilities

- Upload session creation and management
- Chunk tracking for multipart/resumable uploads
- File record CRUD
- Version management
- Folder CRUD
- File move/copy
- Soft delete and restore
- Legal hold management
- Upload completion and processing trigger

### 5.2 Upload Service

```python
# services/file/service.py
class FileService:

    async def create_upload_session(
        self,
        request: CreateUploadSessionRequest,
        auth: AuthContext,
    ) -> UploadSessionResponse:
        # 1. Load and cache project config
        project_config = await self.project_client.get_config(auth.project_id)

        # 2. Validate file against project policies
        await self._validate_upload_policies(request, project_config)

        # 3. Validate metadata against schema
        if project_config.metadata.enforce_schema:
            schema = await self.metadata_service.get_active_schema(auth.project_id)
            await self.metadata_service.validate(request.metadata, schema)

        # 4. Create file record (status=uploading)
        file_record = File(
            organization_id=auth.organization_id,
            project_id=auth.project_id,
            environment_id=auth.environment_id,
            filename=sanitize_filename(request.filename),
            original_filename=request.filename,
            size=request.size,
            mime_type=request.mime_type or "application/octet-stream",
            status=FileStatus.UPLOADING,
            metadata=request.metadata or {},
            tags=request.tags or [],
            uploaded_by_sa=auth.actor_id if auth.actor_type == "service_account" else None,
        )
        self.db.add(file_record)
        await self.db.flush()

        # 5. Create upload session
        if request.size > settings.multipart_threshold:  # 100MB
            upload_session = await self._create_multipart_session(
                file_record, request, project_config
            )
        else:
            upload_session = await self._create_single_upload_session(
                file_record, request, project_config
            )

        return upload_session

    async def complete_upload(
        self,
        session_id: str,
        completion: CompleteUploadRequest,
        auth: AuthContext,
    ) -> FileResponse:
        session = await self._get_upload_session(session_id, auth)
        file_record = await self._get_file(session.file_id, auth)

        # Verify all parts uploaded (multipart)
        if session.upload_type == "multipart":
            await self.storage_client.complete_multipart(
                storage_key=file_record.storage_key,
                upload_id=session.provider_upload_id,
                parts=completion.parts,
            )

        # Update file record
        file_record.status = FileStatus.UPLOAD_COMPLETE
        file_record.checksum_sha256 = completion.checksum_sha256

        # Create initial version
        version = FileVersion(
            organization_id=auth.organization_id,
            file_id=file_record.id,
            project_id=auth.project_id,
            version_number=1,
            storage_key=file_record.storage_key,
            size=file_record.size,
        )
        self.db.add(version)
        await self.db.flush()
        file_record.current_version_id = version.id

        # Emit upload event (transactional outbox)
        await self._emit_event(
            event_type="file.uploaded",
            subject_id=file_record.id,
            payload=FileUploadedPayload.from_file(file_record).model_dump(),
            auth=auth,
        )

        return FileResponse.from_orm(file_record)

    async def _validate_upload_policies(
        self, request: CreateUploadSessionRequest, config: ProjectConfig
    ) -> None:
        # Max file size
        if request.size > config.storage.max_file_size_bytes:
            raise FileTooLargeError(
                actual=request.size,
                maximum=config.storage.max_file_size_bytes,
            )

        # Allowed MIME types
        if config.storage.allowed_mime_types:
            if request.mime_type not in config.storage.allowed_mime_types:
                raise MimeTypeNotAllowedError(
                    mime_type=request.mime_type,
                    allowed=config.storage.allowed_mime_types,
                )

        # WORM: prevent overwrites
        if config.compliance.worm:
            existing = await self.repo.find_by_filename(
                request.filename, auth.project_id
            )
            if existing:
                raise WORMViolationError("Cannot overwrite existing file in WORM project")
```

### 5.3 Download Service

```python
class FileDownloadService:

    async def generate_download_url(
        self,
        file_id: str,
        options: DownloadOptions,
        auth: AuthContext,
    ) -> DownloadURLResponse:
        # 1. Fetch file record
        file_record = await self.repo.get(file_id, auth)
        if not file_record:
            raise FileNotFoundError(file_id)

        # 2. Check status
        if file_record.status == FileStatus.QUARANTINED:
            raise FileQuarantinedError(file_id)
        if file_record.status in (FileStatus.UPLOADING, FileStatus.UPLOAD_COMPLETE):
            raise FileNotReadyError(file_id, file_record.status)

        # 3. Check legal hold (download still allowed, but logged differently)
        legal_hold_active = file_record.legal_hold_active

        # 4. Generate signed URL
        ttl = min(options.ttl_seconds or 3600, 86400)  # Max 24h
        signed_url = await self.storage_client.generate_signed_url(
            storage_key=file_record.storage_key,
            ttl_seconds=ttl,
            content_type=file_record.mime_type,
            content_disposition=f'attachment; filename="{file_record.original_filename}"',
        )

        # 5. Audit log (fire-and-forget)
        asyncio.create_task(
            self.audit.log(
                event_type="file.downloaded",
                subject_id=file_record.id,
                payload={
                    "filename": file_record.filename,
                    "size": file_record.size,
                    "legal_hold_active": legal_hold_active,
                    "ttl_seconds": ttl,
                },
                auth=auth,
            )
        )

        # 6. Increment download count
        asyncio.create_task(self.repo.increment_download_count(file_id))

        return DownloadURLResponse(
            url=signed_url,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
            filename=file_record.original_filename,
            content_type=file_record.mime_type,
            size=file_record.size,
        )
```

### 5.4 Version Management

```python
class FileVersionService:

    async def create_version(
        self,
        file_id: str,
        upload: CreateVersionRequest,
        auth: AuthContext,
    ) -> FileVersionResponse:
        file_record = await self.repo.get(file_id, auth)

        if not project_config.versioning.enabled:
            raise VersioningNotEnabledError(auth.project_id)

        # Increment version number
        new_version_number = file_record.version_count + 1

        # New storage key for this version
        new_storage_key = build_storage_key(
            organization_id=auth.organization_id,
            project_id=auth.project_id,
            environment=auth.environment,
            file_id=file_id,
            version_id=f"v{new_version_number}",
            filename=upload.filename or file_record.filename,
        )

        # ... upload to storage ...

        version = FileVersion(
            file_id=file_id,
            version_number=new_version_number,
            storage_key=new_storage_key,
            size=upload.size,
            metadata_snapshot=file_record.metadata,
            change_note=upload.change_note,
        )
        self.db.add(version)

        file_record.current_version_id = version.id
        file_record.version_count = new_version_number

        await self.db.flush()

        await self._emit_event("file.versioned", file_id, auth)

        return FileVersionResponse.from_orm(version)

    async def rollback_to_version(
        self, file_id: str, version_number: int, auth: AuthContext
    ) -> FileResponse:
        version = await self.version_repo.get_by_number(file_id, version_number)

        # Create a new version pointing to the old storage key
        rollback_version = FileVersion(
            file_id=file_id,
            version_number=file_record.version_count + 1,
            storage_key=version.storage_key,  # Points to old storage
            size=version.size,
            change_note=f"Rollback to version {version_number}",
        )
        self.db.add(rollback_version)
        file_record.current_version_id = rollback_version.id

        return FileResponse.from_orm(file_record)
```

---

## 6. Storage Service

### 6.1 Provider Registry

```python
# services/storage/providers/__init__.py
from .s3 import S3Provider
from .azure import AzureBlobProvider
from .gcs import GCSProvider
from .minio import MinIOProvider
from .r2 import CloudflareR2Provider

PROVIDERS: dict[str, type[StorageProvider]] = {
    "s3": S3Provider,
    "azure_blob": AzureBlobProvider,
    "gcs": GCSProvider,
    "minio": MinIOProvider,
    "r2": CloudflareR2Provider,
}
```

### 6.2 Provider Interface

```python
# services/storage/provider.py
from typing import Protocol, BinaryIO, AsyncIterator
from dataclasses import dataclass

@dataclass
class Part:
    part_number: int
    etag: str

class StorageProvider(Protocol):
    async def upload(
        self,
        key: str,
        data: BinaryIO,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload file. Returns storage key."""
        ...

    async def download_stream(self, key: str) -> AsyncIterator[bytes]:
        """Stream file bytes."""
        ...

    async def delete(self, key: str) -> None: ...

    async def exists(self, key: str) -> bool: ...

    async def copy(
        self, source_key: str, dest_key: str, metadata: dict | None = None
    ) -> str: ...

    async def move(self, source_key: str, dest_key: str) -> str:
        """Default implementation: copy then delete."""
        await self.copy(source_key, dest_key)
        await self.delete(source_key)
        return dest_key

    async def generate_signed_url(
        self,
        key: str,
        ttl_seconds: int,
        method: str = "GET",
        content_type: str | None = None,
        content_disposition: str | None = None,
        response_headers: dict[str, str] | None = None,
    ) -> str: ...

    async def generate_multipart_upload_id(
        self, key: str, content_type: str
    ) -> str: ...

    async def generate_part_upload_url(
        self, key: str, upload_id: str, part_number: int
    ) -> str: ...

    async def complete_multipart(
        self, key: str, upload_id: str, parts: list[Part]
    ) -> str: ...

    async def abort_multipart(self, key: str, upload_id: str) -> None: ...

    async def head(self, key: str) -> dict:
        """Returns size, content_type, etag, last_modified."""
        ...
```

### 6.3 S3 Provider Implementation

```python
# services/storage/providers/s3.py
import aiobotocore.session
from botocore.exceptions import ClientError

class S3Provider:
    def __init__(self, config: S3Config):
        self.config = config
        self._session = aiobotocore.session.get_session()

    def _get_client_kwargs(self) -> dict:
        kwargs = {
            "region_name": self.config.region,
            "aws_access_key_id": self.config.access_key_id,
            "aws_secret_access_key": self.config.secret_access_key,
        }
        if self.config.endpoint_url:  # MinIO, LocalStack, etc.
            kwargs["endpoint_url"] = self.config.endpoint_url
        return kwargs

    async def generate_signed_url(
        self,
        key: str,
        ttl_seconds: int,
        method: str = "GET",
        content_type: str | None = None,
        content_disposition: str | None = None,
        response_headers: dict | None = None,
    ) -> str:
        async with self._session.create_client("s3", **self._get_client_kwargs()) as client:
            params = {
                "Bucket": self.config.bucket_name,
                "Key": key,
            }
            if content_type and method == "PUT":
                params["ContentType"] = content_type
            if content_disposition:
                params["ResponseContentDisposition"] = content_disposition

            client_method = "get_object" if method == "GET" else "put_object"
            url = await client.generate_presigned_url(
                client_method,
                Params=params,
                ExpiresIn=ttl_seconds,
            )
            return url

    async def generate_multipart_upload_id(
        self, key: str, content_type: str
    ) -> str:
        async with self._session.create_client("s3", **self._get_client_kwargs()) as client:
            response = await client.create_multipart_upload(
                Bucket=self.config.bucket_name,
                Key=key,
                ContentType=content_type,
                ServerSideEncryption=self.config.server_side_encryption,
                SSEKMSKeyId=self.config.kms_key_id or "",
            )
            return response["UploadId"]
```

### 6.4 Provider Resolution

```python
# services/storage/resolver.py
class StorageResolver:
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache

    async def get_provider(self, project_id: str, environment: str) -> StorageProvider:
        cache_key = f"storage_provider:{project_id}:{environment}"
        cached = await self.cache.get(cache_key)
        if cached:
            config = StorageConfig.model_validate_json(cached)
        else:
            storage_config_record = await self.db.execute(
                select(StorageConfig).where(
                    StorageConfig.project_id == project_id,
                    StorageConfig.environment == environment,
                    StorageConfig.status == "active",
                )
            )
            config = decrypt_storage_config(storage_config_record.config_encrypted)
            await self.cache.setex(cache_key, 900, config.model_dump_json())

        return PROVIDERS[config.provider](config)
```

---

## 7. Metadata Service

### 7.1 Schema Validation Engine

```python
# services/metadata/validator.py
import jsonschema
from jsonschema import validate, Draft7Validator

class MetadataValidator:
    def __init__(self, cache: Redis):
        self.cache = cache

    async def get_schema(self, project_id: str) -> dict | None:
        cache_key = f"metadata_schema:{project_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return json.loads(cached)

        schema_record = await self.db.execute(
            select(MetadataSchema).where(
                MetadataSchema.project_id == project_id,
                MetadataSchema.is_active == True,
            )
        ).first()

        if not schema_record:
            return None

        await self.cache.setex(cache_key, 300, json.dumps(schema_record.schema))
        return schema_record.schema

    async def validate(self, metadata: dict, schema: dict) -> None:
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(metadata))

        if errors:
            formatted_errors = [
                {
                    "field": ".".join(str(p) for p in e.absolute_path),
                    "message": e.message,
                    "value": e.instance,
                }
                for e in errors
            ]
            raise MetadataValidationError(errors=formatted_errors)
```

---

## 8. Search Service

### 8.1 Indexing

```python
# services/search/indexer.py
from opensearchpy import AsyncOpenSearch

class FileIndexer:
    def __init__(self, client: AsyncOpenSearch):
        self.client = client

    def _index_name(self, project_id: str) -> str:
        return f"filenest-{project_id}"

    async def ensure_index(self, project_id: str, config: SearchConfig) -> None:
        index_name = self._index_name(project_id)
        if not await self.client.indices.exists(index=index_name):
            await self.client.indices.create(
                index=index_name,
                body={
                    "settings": {
                        "number_of_shards": 3,
                        "number_of_replicas": 1,
                        "refresh_interval": "5s",
                    },
                    "mappings": self._get_mappings(config),
                },
            )

    async def index_file(self, file: FileIndexDocument) -> None:
        await self.client.index(
            index=self._index_name(file.project_id),
            id=str(file.file_id),
            body=file.to_search_doc(),
        )

    async def delete_file(self, project_id: str, file_id: str) -> None:
        await self.client.delete(
            index=self._index_name(project_id),
            id=file_id,
            ignore=[404],
        )

    async def search(
        self, project_id: str, query: SearchQuery
    ) -> SearchResults:
        es_query = self._build_query(query)
        response = await self.client.search(
            index=self._index_name(project_id),
            body=es_query,
        )
        return self._parse_results(response)

    def _build_query(self, query: SearchQuery) -> dict:
        must = []
        filter_clauses = []

        # Full-text query
        if query.q:
            must.append({
                "multi_match": {
                    "query": query.q,
                    "fields": ["filename^3", "ocrContent", "metadata.*"],
                    "type": "best_fields",
                }
            })

        # Metadata filters
        if query.filters:
            for field, value in query.filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {f"metadata.{field}": value}})
                else:
                    filter_clauses.append({"term": {f"metadata.{field}": value}})

        # Tag filter
        if query.tags:
            filter_clauses.append({"terms": {"tags": query.tags}})

        # Date range
        if query.created_after or query.created_before:
            date_range = {}
            if query.created_after:
                date_range["gte"] = query.created_after.isoformat()
            if query.created_before:
                date_range["lte"] = query.created_before.isoformat()
            filter_clauses.append({"range": {"createdAt": date_range}})

        return {
            "query": {
                "bool": {
                    "must": must or [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "from": query.offset,
            "size": query.limit,
            "sort": self._build_sort(query.sort_by, query.sort_order),
            "aggs": self._build_aggregations(query.facets) if query.facets else {},
            "highlight": {
                "fields": {
                    "ocrContent": {"number_of_fragments": 3},
                    "filename": {},
                }
            },
        }
```

---

## 9. Processing Service

### 9.1 Worker Architecture

```python
# services/processing/worker.py
import nats
from nats.js import JetStreamContext

class ProcessingWorker:
    def __init__(self, js: JetStreamContext):
        self.js = js
        self.pipeline_executor = PipelineExecutor()

    async def start(self):
        sub = await self.js.subscribe(
            subject="filenest.*.*.file.uploaded",
            durable="processing-workers",
            queue="processing-pool",  # Competing consumers
            config=nats.js.api.ConsumerConfig(
                ack_policy=nats.js.api.AckPolicy.EXPLICIT,
                max_deliver=3,
                ack_wait=300,  # 5 min per job
                max_ack_pending=50,  # Max 50 in-flight per worker
            ),
        )

        async for msg in sub.messages:
            try:
                event = FileUploadedEvent.model_validate_json(msg.data)
                await self.pipeline_executor.execute(event)
                await msg.ack()
            except PermanentFailure as e:
                logger.error(f"Permanent failure for {event.payload.file_id}: {e}")
                await msg.term()  # Send to dead letter
            except Exception as e:
                logger.warning(f"Transient failure for {event.payload.file_id}: {e}")
                await msg.nak(delay=backoff_delay(msg.metadata.num_delivered))
```

### 9.2 Pipeline Executor

```python
# services/processing/pipeline.py
class PipelineExecutor:
    STAGE_REGISTRY: dict[str, type[PipelineStage]] = {
        "virus_scan": VirusScanStage,
        "mime_validation": MimeValidationStage,
        "ocr": OCRStage,
        "phi_detection": PHIDetectionStage,
        "pii_detection": PIIDetectionStage,
        "classification": ClassificationStage,
        "thumbnail": ThumbnailStage,
        "preview": PreviewStage,
        "embedding": EmbeddingStage,
        "indexing": IndexingStage,
    }

    async def execute(self, event: FileUploadedEvent) -> None:
        project_config = await self.project_client.get_config(event.project_id)
        pipeline_stages = self._resolve_stages(project_config.processing)

        job = await self.job_repo.create(
            file_id=event.payload.file_id,
            pipeline_config=project_config.processing.model_dump(),
        )

        # Run parallel stages first
        parallel_stages = ["virus_scan", "mime_validation"]
        sequential_stages = [s for s in pipeline_stages if s not in parallel_stages]

        try:
            # Parallel execution
            parallel_tasks = [
                self._run_stage(job, stage_name, event)
                for stage_name in parallel_stages
                if stage_name in pipeline_stages
            ]
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

            # Check for virus — halt pipeline if infected
            if any(isinstance(r, VirusDetectedError) for r in parallel_results):
                await self._quarantine_file(event.payload.file_id)
                await self.job_repo.mark_failed(job.id, "Virus detected")
                return

            # Sequential execution
            for stage_name in sequential_stages:
                await self._run_stage(job, stage_name, event)

            await self.job_repo.mark_completed(job.id)

            # Emit completion event
            await self.event_publisher.publish(
                event_type="file.processed",
                subject_id=event.payload.file_id,
                payload=ProcessingCompletePayload(
                    file_id=event.payload.file_id,
                    stages_completed=pipeline_stages,
                    ocr_extracted=project_config.processing.ocr,
                ).model_dump(),
                organization_id=event.organization_id,
                project_id=event.project_id,
            )

        except Exception as e:
            await self.job_repo.mark_failed(job.id, str(e))
            raise

    async def _run_stage(
        self, job: ProcessingJob, stage_name: str, event: FileUploadedEvent
    ) -> None:
        stage_class = self.STAGE_REGISTRY[stage_name]
        stage = stage_class(self.storage_client, self.db)

        await self.job_repo.update_stage(job.id, stage_name, "running")
        start = time.monotonic()

        try:
            result = await stage.execute(event)
            duration_ms = int((time.monotonic() - start) * 1000)
            await self.job_repo.complete_stage(job.id, stage_name, result, duration_ms)
        except Exception as e:
            await self.job_repo.fail_stage(job.id, stage_name, str(e))
            raise
```

### 9.3 Virus Scan Stage

```python
# services/processing/stages/virus_scan.py
import clamd

class VirusScanStage:
    async def execute(self, event: FileUploadedEvent) -> dict:
        # Download file from storage
        stream = await self.storage_client.download_stream(event.payload.storage_key)
        file_bytes = b"".join([chunk async for chunk in stream])

        # Scan with ClamAV
        scanner = clamd.ClamdNetworkSocket(host="clamav", port=3310)
        result = scanner.instream(io.BytesIO(file_bytes))

        scan_result = result.get("stream", ("UNKNOWN", None))
        status = scan_result[0]  # 'OK', 'FOUND', 'ERROR'

        if status == "FOUND":
            threat_name = scan_result[1]
            # Update file record to quarantined
            await self.file_repo.quarantine(
                file_id=event.payload.file_id,
                threat=threat_name,
            )
            raise VirusDetectedError(threat=threat_name)

        return {
            "provider": "clamav",
            "result": "clean" if status == "OK" else "error",
            "scanned_at": datetime.utcnow().isoformat(),
            "file_size": len(file_bytes),
        }
```

---

## 10. Audit Service

### 10.1 Audit Logger

```python
# services/audit/logger.py
class AuditLogger:
    """
    The audit logger writes to the transactional outbox (events table)
    in the same DB transaction as the business operation.
    The outbox worker then persists to audit_logs.
    This guarantees audit log completeness.
    """

    async def log(
        self,
        event_type: str,
        subject_type: str,
        subject_id: str | None,
        payload: dict,
        auth: AuthContext,
        request: Request | None = None,
        phi_involved: bool = False,
        db: AsyncSession | None = None,
    ) -> None:
        audit_entry = AuditLog(
            organization_id=auth.organization_id,
            project_id=auth.project_id,
            event_type=event_type,
            subject_type=subject_type,
            subject_id=subject_id,
            actor_type=auth.actor_type,
            actor_id=auth.actor_id,
            actor_name=auth.actor_name,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_id=request.headers.get("x-request-id") if request else None,
            payload=payload,
            phi_involved=phi_involved,
            compliance_relevant=phi_involved or event_type.startswith("compliance."),
        )

        session = db or self.db
        session.add(audit_entry)
        # Committed with the parent transaction — atomic
```

### 10.2 Audit Export

```python
class AuditExportService:
    async def create_export(
        self,
        params: AuditExportParams,
        auth: AuthContext,
    ) -> AuditExport:
        export = AuditExport(
            organization_id=auth.organization_id,
            status="generating",
            params=params.model_dump(),
        )
        self.db.add(export)
        await self.db.flush()

        # Trigger async export
        asyncio.create_task(self._generate_export(export.id, params, auth))

        return export

    async def _generate_export(
        self, export_id: str, params: AuditExportParams, auth: AuthContext
    ) -> None:
        query = (
            select(AuditLog)
            .where(
                AuditLog.organization_id == auth.organization_id,
                AuditLog.occurred_at >= params.date_from,
                AuditLog.occurred_at <= params.date_to,
            )
        )
        if params.event_types:
            query = query.where(AuditLog.event_type.in_(params.event_types))

        # Stream to storage
        key = f"exports/{auth.organization_id}/audit-{export_id}.csv"
        async with self.storage.streaming_write(key) as writer:
            await writer.write(CSV_HEADERS)
            async for row in self.db.stream(query):
                await writer.write(format_audit_row(row))

        export_url = await self.storage.generate_signed_url(key, ttl_seconds=3600)
        await self.export_repo.mark_ready(export_id, download_url=export_url)
```

---

## 11. Webhook Service

### 11.1 Delivery Worker

```python
# services/webhook/worker.py
class WebhookDeliveryWorker:
    async def process_event(self, event: dict) -> None:
        webhooks = await self.webhook_repo.get_subscribed(
            project_id=event["project_id"],
            event_type=event["event_type"],
        )

        for webhook in webhooks:
            await self._deliver(webhook, event)

    async def _deliver(self, webhook: Webhook, event: dict) -> None:
        payload = json.dumps(event)
        signature = self._sign_payload(payload, webhook.signing_secret)

        headers = {
            "Content-Type": "application/json",
            "X-FileNest-Event": event["event_type"],
            "X-FileNest-Signature": f"sha256={signature}",
            "X-FileNest-Delivery": str(uuid4()),
            "X-FileNest-Timestamp": str(int(time.time())),
        }

        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event["event_type"],
            event_id=event["event_id"],
            request_payload=event,
            request_headers=headers,
        )
        self.db.add(delivery)

        async with httpx.AsyncClient(timeout=webhook.timeout_seconds) as client:
            try:
                response = await client.post(
                    webhook.url,
                    content=payload,
                    headers=headers,
                )
                delivery.status = "delivered" if response.is_success else "failed"
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:2048]
                delivery.delivered_at = datetime.utcnow()

                if not response.is_success:
                    await self._schedule_retry(delivery)

            except Exception as e:
                delivery.status = "failed"
                delivery.response_body = str(e)
                await self._schedule_retry(delivery)

    def _sign_payload(self, payload: str, secret: str) -> str:
        return hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    async def _schedule_retry(self, delivery: WebhookDelivery) -> None:
        if delivery.attempt_count >= delivery.webhook.max_retries:
            delivery.status = "dead_lettered"
            await self.webhook_repo.mark_failing(delivery.webhook_id)
            return

        delay = 2 ** delivery.attempt_count * 30  # Exponential backoff: 30s, 60s, 120s...
        delivery.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay)
        delivery.attempt_count += 1
        delivery.status = "pending"
```

---

## 12. Compliance Service

### 12.1 Policy Engine

```python
# services/compliance/policy_engine.py
class CompliancePolicyEngine:

    async def check_delete_allowed(
        self, file_id: str, auth: AuthContext
    ) -> PolicyCheckResult:
        file = await self.file_repo.get(file_id, auth)

        violations = []

        # WORM check
        if file.worm_committed:
            violations.append(PolicyViolation(
                policy="worm",
                message="WORM-committed files cannot be deleted",
            ))

        # Legal hold check
        if file.legal_hold_active:
            violations.append(PolicyViolation(
                policy="legal_hold",
                reason=file.legal_hold_reason,
                message="File is under legal hold and cannot be deleted",
            ))

        # Folder legal hold check
        if file.folder_id:
            folder = await self.folder_repo.get(file.folder_id)
            if folder and folder.legal_hold_active:
                violations.append(PolicyViolation(
                    policy="folder_legal_hold",
                    message="Parent folder is under legal hold",
                ))

        # Retention policy check
        if file.retain_until and file.retain_until > datetime.utcnow():
            days_remaining = (file.retain_until - datetime.utcnow()).days
            violations.append(PolicyViolation(
                policy="retention",
                message=f"File under retention policy. {days_remaining} days remaining.",
            ))

        return PolicyCheckResult(
            allowed=len(violations) == 0,
            violations=violations,
        )

    async def apply_legal_hold(
        self, file_id: str, reason: str, auth: AuthContext
    ) -> None:
        file = await self.file_repo.get(file_id, auth)
        file.legal_hold_active = True
        file.legal_hold_reason = reason
        file.legal_hold_set_by = auth.actor_id
        file.legal_hold_set_at = datetime.utcnow()

        await self.audit.log(
            event_type="file.legal_hold_set",
            subject_id=file_id,
            payload={"reason": reason},
            auth=auth,
        )

    async def commit_worm(self, file_id: str, auth: AuthContext) -> None:
        """WORM commit is IRREVERSIBLE."""
        project_config = await self.project_client.get_config(auth.project_id)
        if not project_config.compliance.worm:
            raise WORMNotEnabledError(auth.project_id)

        file = await self.file_repo.get(file_id, auth)
        if file.worm_committed:
            raise AlreadyWORMError(file_id)

        file.worm_committed = True
        file.worm_committed_at = datetime.utcnow()
```

---

## 13. Healthcare Service

### 13.1 FHIR Resource Mapper

```python
# services/healthcare/fhir_mapper.py
class FHIRMapper:
    def file_to_document_reference(
        self, file: File, fhir_metadata: FHIRMetadata
    ) -> dict:
        """Map a FileNest file to a FHIR R4 DocumentReference."""
        return {
            "resourceType": "DocumentReference",
            "id": f"fn-{file.id}",
            "status": "current",
            "docStatus": "final" if file.status == "ready" else "preliminary",
            "type": self._get_document_type(file.metadata.get("documentType")),
            "subject": {
                "reference": f"Patient/{file.metadata.get('patientId')}"
            },
            "date": file.created_at.isoformat(),
            "author": self._get_author(file),
            "content": [
                {
                    "attachment": {
                        "contentType": file.mime_type,
                        "size": file.size,
                        "title": file.original_filename,
                        "url": fhir_metadata.content_url,
                        "hash": file.checksum_sha256,
                    }
                }
            ],
            "context": {
                "encounter": [
                    {
                        "reference": f"Encounter/{file.metadata.get('encounterId')}"
                    }
                ] if file.metadata.get("encounterId") else [],
                "facilityType": self._get_facility_type(file.metadata),
                "practiceSetting": self._get_practice_setting(file.metadata),
            },
            "meta": {
                "source": "urn:filenest",
                "tag": [
                    {
                        "system": "urn:filenest:project",
                        "code": str(file.project_id)
                    }
                ]
            }
        }
```

---

## 14. Inter-Service Communication

### 14.1 HTTP Client with Circuit Breaker

```python
# shared/clients/base.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class ServiceClient:
    def __init__(self, base_url: str, service_name: str):
        self.base_url = base_url
        self.service_name = service_name
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(5.0, connect=1.0),
            headers={"X-Service-Name": "filenest-file-service"},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get(self, path: str, **kwargs) -> dict:
        with tracer.start_as_current_span(f"{self.service_name}.get"):
            response = await self._client.get(path, **kwargs)
            response.raise_for_status()
            return response.json()
```

### 14.2 NATS Event Publisher (Transactional Outbox)

```python
# shared/messaging/outbox.py
class TransactionalOutboxPublisher:
    """
    Writes events to the events table in the same transaction as business logic.
    Separate outbox worker polls and publishes to NATS.
    This guarantees at-least-once delivery without distributed transactions.
    """

    async def publish(
        self,
        event_type: str,
        subject_id: str,
        payload: dict,
        organization_id: str,
        project_id: str,
        db: AsyncSession,
    ) -> None:
        event = Event(
            organization_id=organization_id,
            project_id=project_id,
            event_type=event_type,
            subject_id=subject_id,
            payload=payload,
            status="pending",
        )
        db.add(event)
        # Committed with parent transaction

class OutboxWorker:
    """Background task that polls events table and publishes to NATS."""

    async def run(self) -> None:
        while True:
            async with get_db_session() as db:
                pending = await db.execute(
                    select(Event)
                    .where(Event.status == "pending")
                    .order_by(Event.created_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)  # Prevent double processing
                )

                for event in pending.scalars():
                    try:
                        await self.nats.publish(
                            subject=f"filenest.{event.organization_id}.{event.project_id}.{event.event_type}",
                            payload=event.payload,
                        )
                        event.status = "published"
                        event.published_at = datetime.utcnow()
                    except Exception:
                        event.attempt_count += 1
                        if event.attempt_count >= 5:
                            event.status = "failed"

            await asyncio.sleep(1)  # Poll every second
```

---

## 15. Error Handling

### 15.1 Exception Hierarchy

```python
# shared/exceptions/__init__.py
class FileNestError(Exception):
    status_code: int = 500
    error_code: str = "internal_error"
    message: str = "An internal error occurred"

class NotFoundError(FileNestError):
    status_code = 404
    error_code = "not_found"

class FileNotFoundError(NotFoundError):
    def __init__(self, file_id: str):
        self.file_id = file_id
        self.message = f"File {file_id} not found"
        self.error_code = "file_not_found"

class AuthenticationError(FileNestError):
    status_code = 401
    error_code = "unauthorized"

class AuthorizationError(FileNestError):
    status_code = 403
    error_code = "forbidden"

class MetadataValidationError(FileNestError):
    status_code = 422
    error_code = "metadata_validation_failed"
    def __init__(self, errors: list[dict]):
        self.validation_errors = errors

class WORMViolationError(FileNestError):
    status_code = 409
    error_code = "worm_violation"

class LegalHoldViolationError(FileNestError):
    status_code = 409
    error_code = "legal_hold_active"

class FileTooLargeError(FileNestError):
    status_code = 413
    error_code = "file_too_large"
```

### 15.2 Global Exception Handler

```python
# shared/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse

async def filenest_exception_handler(
    request: Request, exc: FileNestError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "request_id": request.headers.get("x-request-id"),
                **({"validation_errors": exc.validation_errors}
                   if hasattr(exc, "validation_errors") else {}),
            }
        },
    )
```

---

## 16. Observability

### 16.1 Structured Logging

```python
# shared/logging/__init__.py
import structlog

def setup_logging(service_name: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.WriteLoggerFactory(),
    )

# Usage in services
logger = structlog.get_logger()

async def handle_upload(file_id: str, auth: AuthContext):
    logger.info(
        "file_upload_started",
        file_id=file_id,
        organization_id=auth.organization_id,
        project_id=auth.project_id,
    )
```

### 16.2 Request ID Middleware

```python
# shared/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 16.3 OpenTelemetry Integration

```python
# shared/telemetry/__init__.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def init_telemetry(service_name: str) -> None:
    provider = TracerProvider(
        resource=Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: "1.0.0",
            DEPLOYMENT_ENVIRONMENT: settings.env,
        })
    )

    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.otel_endpoint)
        )
    )

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
```
