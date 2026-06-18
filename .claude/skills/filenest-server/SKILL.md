# FileNest — Server-Side Component Skill

## Purpose
Build and scaffold **server-side components** for the FileNest platform.
Covers: FastAPI services (clean architecture), shared infrastructure, Node.js SDK,
Python SDK, Next.js server components / server actions / route handlers / webhooks.

## When to invoke
- User asks to add a new FastAPI service or extend an existing one
- User asks to implement a new endpoint, service method, or repository method
- User asks to use the Node.js SDK (`@filenest/node`) or Python SDK (`filenest`) on the server
- User asks to build Next.js server components, server actions, or webhook handlers
- User asks to wire up auth, NATS events, audit logging, or processing pipelines

---

## Modules Folder Structure — `modules/server/` and `modules/entities/`

Server-only code and shared types live in two separate layers. Never import from `modules/server/` in client components.

```
modules/
├── entities/                      # Framework-free types and Zod schemas (safe in both environments)
│   └── schemas/                   # One file per domain entity: file.ts, project.ts, organization.ts
└── server/                        # Server-only Next.js code
    ├── auth/                      # getServerSession(), session types, auth helpers
    ├── actions/                   # zsa server actions — one file per feature
    │   ├── project.actions.ts
    │   ├── file.actions.ts
    │   └── org.actions.ts
    └── utils/                     # Shared server utilities (formatting, fetch helpers)
```

### Rules for `modules/server/`

- **Server actions use zsa** (`createServerAction`) — never plain async functions called directly from client.
- **Always call `revalidatePath()`** in mutation actions so the page re-fetches after write.
- **Auth check first** — every action/route handler calls `getServerSession()` and throws/redirects if no session.
- **`modules/entities/schemas/`** contains Zod schemas; import them in both actions and client validation — never duplicate schemas.
- **Split by feature** — one file per domain in `server/actions/` (e.g. `file.actions.ts`, `project.actions.ts`).
- **No business logic in route handlers** — route handlers call server actions or `filenestServer()` SDK methods, then `revalidatePath()`. That's it.

---

## Clean Architecture: Every Service Follows This Layout

```
services/{name}/
├── main.py          # FastAPI app factory (create_app)
├── router.py        # Route registration (prefix="/v1")
├── routes/          # HTTP handlers — thin, delegate to service
│   └── *.py
├── service.py       # Business logic — the only place for rules
├── repository.py    # DB queries — no business logic here
├── schemas.py       # Pydantic request/response models
├── dependencies.py  # FastAPI Depends() wiring
└── events.py        # NATS event publishers (outbox writes)
```

**Dependency rule:** routes → service → repository → DB. No layer skips another.

---

## App Factory Pattern

```python
# services/{name}/main.py
from fastapi import FastAPI
from shared.database import init_db
from shared.cache import init_redis
from shared.messaging import init_nats
from shared.telemetry import init_telemetry
from shared.logging import setup_logging
from .router import router
from .middleware import TenantContextMiddleware, RequestIDMiddleware

def create_app() -> FastAPI:
    app = FastAPI(title="FileNest {Name} Service", version="1.0.0",
                  docs_url="/docs" if settings.env != "production" else None)

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.include_router(router, prefix="/v1")

    @app.on_event("startup")
    async def startup():
        await init_db()
        await init_redis()
        await init_nats()
        init_telemetry(service_name="{name}-service")
        setup_logging(service_name="{name}-service")

    return app
```

---

## Auth & Tenant Context

```python
# shared/auth/middleware.py — authentication (token → AuthContext)
# shared/auth/tenant.py    — ContextVar holding current tenant
# shared/auth/permissions.py — scope-based authorization

# In dependencies.py — use these Depends():
from shared.auth.tenant import require_auth
from shared.auth.permissions import require_scope

# Route example:
@router.post("/files", response_model=FileResponse)
async def upload_file(
    body: CreateUploadSessionRequest,
    auth: AuthContext = Depends(require_scope("files:upload")),
    service: FileService = Depends(get_file_service),
):
    return await service.create_upload_session(body, auth)
```

Token prefixes:
- `fn_live_...` / `fn_test_...` → API key (server-to-server)
- `fn_sa_...` → Service account
- `fn_upload_token_...` → Short-lived browser token (constrained scopes only)

Scopes: `files:upload`, `files:download`, `files:read`, `files:delete`,
`files:update_metadata`, `api_keys:create`, `api_keys:revoke`,
`projects:read`, `projects:update`, `audit:read`, `compliance:manage`

---

## Database Session (shared/database/session.py)

```python
# Write queries use primary engine; read queries use read replica
from shared.database import get_db, get_read_db

# In dependencies.py:
async def get_file_service(
    db: AsyncSession = Depends(get_db),
    read_db: AsyncSession = Depends(get_read_db),
    cache: Redis = Depends(get_redis),
) -> FileService:
    return FileService(db=db, read_db=read_db, cache=cache)
```

Session auto-commits on success, auto-rolls back on exception. Never call `db.commit()` manually inside a service — the session context manager handles it.

---

## Repository Pattern

```python
# services/{name}/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from shared.models import File

class FileRepository:
    def __init__(self, db: AsyncSession, read_db: AsyncSession):
        self.db = db
        self.read_db = read_db

    async def get(self, file_id: str, auth: AuthContext) -> File | None:
        result = await self.read_db.execute(
            select(File).where(
                File.id == file_id,
                File.organization_id == auth.organization_id,
                File.project_id == auth.project_id,
                File.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, file: File) -> File:
        self.db.add(file)
        await self.db.flush()   # Get the DB-assigned id without committing
        return file

    async def soft_delete(self, file_id: str, auth: AuthContext) -> None:
        await self.db.execute(
            update(File)
            .where(File.id == file_id, File.organization_id == auth.organization_id)
            .values(deleted_at=datetime.utcnow())
        )
```

---

## Service Layer (business logic)

```python
# services/{name}/service.py
class FileService:
    def __init__(self, db, read_db, cache, repo=None, audit=None, event_publisher=None):
        self.db = db
        self.repo = repo or FileRepository(db, read_db)
        self.audit = audit or AuditLogger(db)
        self.events = event_publisher or TransactionalOutboxPublisher()

    async def create_upload_session(
        self, request: CreateUploadSessionRequest, auth: AuthContext
    ) -> UploadSessionResponse:
        # 1. Load project config
        project_config = await self.project_client.get_config(auth.project_id)

        # 2. Validate against policies
        await self._validate_upload_policies(request, project_config)

        # 3. Validate metadata schema if enforced
        if project_config.metadata.enforce_schema:
            schema = await self.metadata_service.get_active_schema(auth.project_id)
            await self.metadata_service.validate(request.metadata, schema)

        # 4. Persist file record (status=uploading)
        file_record = File(
            organization_id=auth.organization_id,
            project_id=auth.project_id,
            filename=sanitize_filename(request.filename),
            original_filename=request.filename,
            size=request.size,
            mime_type=request.mime_type or "application/octet-stream",
            status=FileStatus.UPLOADING,
            metadata=request.metadata or {},
        )
        await self.repo.create(file_record)

        # 5. Generate presigned upload URL from storage provider
        upload_session = await self._create_upload_session(file_record, request, project_config)
        return upload_session
```

---

## Transactional Outbox (events)

```python
# services/{name}/events.py
# Write event to DB in the SAME transaction as the business operation.
# OutboxWorker polls and publishes to NATS separately.

from shared.messaging.outbox import TransactionalOutboxPublisher

class FileEventPublisher:
    def __init__(self, db: AsyncSession):
        self.publisher = TransactionalOutboxPublisher()
        self.db = db

    async def file_uploaded(self, file: File, auth: AuthContext) -> None:
        await self.publisher.publish(
            event_type="file.uploaded",
            subject_id=str(file.id),
            payload=FileUploadedPayload.from_file(file).model_dump(),
            organization_id=auth.organization_id,
            project_id=auth.project_id,
            db=self.db,
        )
```

NATS subject format: `filenest.{org_id}.{project_id}.{event_type}`
Events: `file.uploaded`, `file.processed`, `file.deleted`, `file.versioned`,
`file.virus_detected`, `file.legal_hold_set`, `file.worm_committed`

---

## Audit Logging

```python
# Audit logger writes to the same transaction — guaranteed completeness
await self.audit.log(
    event_type="file.deleted",
    subject_type="file",
    subject_id=str(file_id),
    payload={"filename": file.filename, "size": file.size},
    auth=auth,
    request=request,          # Optional: captures IP + user-agent
    phi_involved=False,
    db=self.db,
)
```

Always audit: create, delete, download, legal hold changes, WORM commits, metadata updates.

---

## Exception Hierarchy (shared/exceptions)

```python
# Raise these — the global handler converts them to JSON responses
from shared.exceptions import (
    FileNotFoundError,        # 404
    AuthenticationError,      # 401
    AuthorizationError,       # 403
    MetadataValidationError,  # 422 — pass errors=[{field, message, value}]
    WORMViolationError,       # 409
    LegalHoldViolationError,  # 409
    FileTooLargeError,        # 413
    FileQuarantinedError,     # 409
)
```

---

## Storage Provider (injected, never hardcoded)

```python
# services/storage/resolver.py — resolves provider from project config
from services.storage.resolver import StorageResolver

provider = await storage_resolver.get_provider(auth.project_id, auth.environment)

# Provider interface methods:
await provider.generate_signed_url(key, ttl_seconds=3600, method="PUT")
await provider.generate_multipart_upload_id(key, content_type)
await provider.generate_part_upload_url(key, upload_id, part_number)
await provider.complete_multipart(key, upload_id, parts)
await provider.delete(key)
await provider.copy(source_key, dest_key)
await provider.download_stream(key)   # AsyncIterator[bytes]
```

Supported providers: `s3`, `azure_blob`, `gcs`, `minio`, `r2` — resolved from DB config per project.

---

## Processing Pipeline (services/processing)

```python
# New stages must implement:
class MyStage:
    async def execute(self, event: FileUploadedEvent) -> dict:
        # Return dict of stage results
        ...

# Register in PipelineExecutor.STAGE_REGISTRY:
STAGE_REGISTRY = {
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
```

`virus_scan` and `mime_validation` run in parallel first. If virus found → quarantine + halt. All others run sequentially.

---

## Node.js SDK (`@filenest/node`) — server-side usage

```typescript
import { FileNest } from '@filenest/node';

const filenest = new FileNest({
  apiKey: process.env.FILENEST_API_KEY!,
  projectId: process.env.FILENEST_PROJECT_ID!,
  environment: 'production',
});

// Upload (Buffer or Stream)
const file = await filenest.files.upload({
  filename: 'report.pdf',
  data: buffer,
  mimeType: 'application/pdf',
  metadata: { patientId: 'P-12345', documentType: 'LabReport' },
  tags: ['clinical'],
});

// List with metadata filters
const { data, pagination } = await filenest.files.list({
  metadata: { patientId: 'P-12345' },
  sortBy: 'created_at',
  sortOrder: 'desc',
  limit: 20,
});

// Signed download URL
const { url, expiresAt } = await filenest.files.getDownloadUrl('file_xyz', { ttl: 3600 });

// Search
const results = await filenest.search.query({
  q: 'lab report',
  filters: { metadata: { patientId: 'P-12345' }, tags: ['urgent'] },
  facets: ['documentType'],
});

// Generate upload token for frontend
const token = await filenest.uploadTokens.create({
  maxSize: 50 * 1024 * 1024,
  allowedMimeTypes: ['application/pdf', 'image/*'],
  maxFiles: 5,
  folderId: 'folder_abc',
  metadata: { uploadedBy: userId },
  expiresIn: 3600,
});

// Compliance
await filenest.compliance.setLegalHold('file_xyz', { reason: 'Audit 2026-Q2', indefinite: true });
await filenest.compliance.commitWorm('file_xyz', { confirm: true, reason: 'SEC requirement' });

// Webhook verification
const isValid = filenest.webhooks.verify(rawBody, signatureHeader, process.env.WEBHOOK_SECRET!);
```

---

## Next.js Server Components

```tsx
// app/patients/[patientId]/documents/page.tsx
import { filenestServer } from '@filenest/nextjs/server';

const fn = filenestServer({
  apiKey: process.env.FILENEST_API_KEY!,
  projectId: process.env.FILENEST_PROJECT_ID!,
});

export default async function PatientDocumentsPage({ params }: { params: { patientId: string } }) {
  const { data: files } = await fn.files.list({
    metadata: { patientId: params.patientId },
    sortBy: 'created_at',
    sortOrder: 'desc',
    limit: 50,
  });

  return (
    <ul>
      {files.map(file => (
        <li key={file.id}>{file.filename} — {file.metadata.documentType}</li>
      ))}
    </ul>
  );
}
```

---

## Next.js Server Actions

```typescript
// app/actions/files.ts
'use server';
import { filenestServer } from '@filenest/nextjs/server';
import { revalidatePath } from 'next/cache';
import { auth } from '@/auth';

const fn = filenestServer({
  apiKey: process.env.FILENEST_API_KEY!,
  projectId: process.env.FILENEST_PROJECT_ID!,
});

export async function uploadFile(formData: FormData) {
  const session = await auth();
  if (!session) throw new Error('Unauthorized');

  const file = formData.get('file') as File;
  const patientId = formData.get('patientId') as string;

  const result = await fn.files.upload({
    filename: file.name,
    data: Buffer.from(await file.arrayBuffer()),
    mimeType: file.type,
    metadata: { patientId, documentType: 'LabReport', uploadedBy: session.user.id },
  });

  revalidatePath('/patients/' + patientId);
  return result;
}

export async function deleteFile(fileId: string) {
  await fn.files.delete(fileId);
  revalidatePath('/files');
}
```

---

## Next.js Token Endpoint (Route Handler)

```typescript
// app/api/filenest-token/route.ts
import { createUploadToken } from '@filenest/nextjs/server';
import { auth } from '@/auth';

export async function POST(req: Request) {
  const session = await auth();
  if (!session) return Response.json({ error: 'Unauthorized' }, { status: 401 });

  const { folderId, documentType } = await req.json();

  const token = await createUploadToken({
    apiKey: process.env.FILENEST_API_KEY!,
    projectId: process.env.FILENEST_PROJECT_ID!,
    constraints: {
      maxSize: 50 * 1024 * 1024,
      allowedMimeTypes: ['application/pdf', 'image/*'],
      maxFiles: 10,
    },
    metadata: { uploadedBy: session.user.id, documentType: documentType || 'general' },
    folderId,
    expiresIn: 3600,
  });

  return Response.json(token);
}
```

---

## Next.js Webhook Handler

```typescript
// app/api/webhooks/filenest/route.ts
import { verifyWebhookSignature, parseWebhookEvent } from '@filenest/nextjs/server';

export async function POST(req: Request) {
  const body = await req.text();
  const signature = req.headers.get('x-filenest-signature') ?? '';

  if (!verifyWebhookSignature(body, signature, process.env.FILENEST_WEBHOOK_SECRET!)) {
    return new Response('Invalid signature', { status: 401 });
  }

  const event = parseWebhookEvent(body);

  switch (event.type) {
    case 'file.uploaded':    await handleFileUploaded(event.data);   break;
    case 'file.processed':   await handleFileProcessed(event.data);  break;
    case 'file.virus_detected': await handleVirus(event.data);       break;
  }

  return new Response('OK', { status: 200 });
}
```

---

## Python SDK (`filenest`) — server-side usage

```python
from filenest import FileNest, AsyncFileNest

# Sync client
fn = FileNest(api_key=os.environ["FILENEST_API_KEY"], project_id=os.environ["FILENEST_PROJECT_ID"])

# Async client (preferred in FastAPI/async context)
async with AsyncFileNest(api_key=..., project_id=...) as fn:
    file = await fn.files.upload(
        filename="report.pdf",
        data=pdf_bytes,
        mime_type="application/pdf",
        metadata={"patientId": "P-12345", "documentType": "LabReport"},
    )
    url = await fn.files.get_download_url(file.id, ttl=3600)

# FastAPI dependency pattern
from functools import lru_cache

@lru_cache(maxsize=1)
def get_filenest() -> AsyncFileNest:
    return AsyncFileNest(api_key=settings.FILENEST_API_KEY, project_id=settings.FILENEST_PROJECT_ID)

# Webhook verification
from filenest import verify_webhook_signature
if not verify_webhook_signature(body, signature, settings.WEBHOOK_SECRET):
    raise HTTPException(status_code=401, detail="Invalid signature")
```

---

## Structured Logging

```python
import structlog
logger = structlog.get_logger()

# Always include tenant context in log entries
logger.info("file_upload_started",
    file_id=file_id,
    organization_id=auth.organization_id,
    project_id=auth.project_id,
    size=request.size,
)
```

---

## Key rules

1. **Routes are thin** — validate input via Pydantic schemas, call one service method, return response model.
2. **Service owns all business logic** — no raw SQL or storage calls in routes or repositories.
3. **Repository owns all DB access** — always include `organization_id` + `project_id` in queries (RLS enforcement).
4. **Always use the outbox for events** — never publish directly to NATS from a service method.
5. **Audit every mutation** — upload, delete, download, legal-hold, WORM, metadata-update.
6. **Storage provider is injected** — never import a specific provider class directly in service code.
7. **`await db.flush()` not `await db.commit()`** — the session context manager commits; flush just gets the DB-assigned id.
8. **Config from `ProjectConfig`** — industry-specific behaviour (HIPAA, WORM, retention) comes from project config, never hardcoded conditionals.
