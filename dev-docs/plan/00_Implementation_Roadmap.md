# FileNest — Implementation Roadmap

**Version:** 2.1.0
**Target:** v1.0 Production Release
**Last Updated:** 2026-06-20

---

## Overview

This roadmap takes the current scaffold to a full **v1.0 production release** across 7 phases.

**Scope of v1.0:** Everything — file infrastructure, processing, search, webhooks, console app, SDKs, observability, storage providers, sharing, previews, bulk operations.

**Included in v1.0 — Compliance foundations:** HIPAA technical safeguards, GDPR data subject rights (erasure, portability, DSARs), PHI/PII detection in the processing pipeline, legal hold framework, retention enforcement, audit log immutability.

**Explicitly out of v1.0 → v2.0 — Domain Compliance Packs:** WORM enforcement (S3 Object Lock / immutable storage), domain-specific presets for finance, insurance, and government, FHIR/XDS clinical integration, customer-managed KMS envelope encryption (BYOK), advanced PHI redaction workflows. These require their own phase after v1.0 ships. The compliance modules are already scaffolded in the codebase following clean architecture so they can be dropped in without touching existing code.

**Architecture:** Modular monolith — all domain logic in `backend/` as isolated modules (files, projects, processing, search, webhooks, etc.). Each module owns its own service, repository, schemas, and router. No cross-module DB joins. Cross-module work goes through the NATS transactional outbox. When a module needs to become its own service, the refactor is mechanical — no business logic changes needed.

**Pre-existing:** The IAM (`iam/`) is already complete. It handles users, organisations, API keys (`fn_live_` / `fn_test_`), and OAuth 2.1 PKCE. The `backend/` scaffold exists with the core directory structure and wiring. The frontend auth skeleton (login, callback, onboarding) is started.

---

## Phase Overview

| Phase | Name | Duration | Gate |
|-------|------|----------|------|
| 1 | Foundation | Weeks 1–4 | File upload and download work end-to-end via `curl` |
| 2 | Processing & Events | Weeks 4–8 | Virus scan runs on every upload; webhooks fire |
| 3 | Metadata, Search & Folders | Weeks 7–12 | Full-text + metadata search returns results |
| 4 | Console App | Weeks 9–16 | Developer can manage everything without hitting raw API |
| 5 | SDKs & Developer Experience | Weeks 13–18 | Node and Python SDKs work; docs live |
| 6 | Production Infrastructure | Weeks 16–23 | Observable, rate-limited, deployed on Kubernetes |
| 7 | Advanced Features | Weeks 20–30 | All storage providers, previews, sharing, bulk ops |

Phases 3, 4, and 5 run in parallel after Phase 2.
Phases 6 and 7 overlap — start Phase 7 when Phase 6 is 60% done.

---

## PHASE 1 — Foundation

**Duration:** Weeks 1–4
**Goal:** Working backend with auth, project CRUD, and single-file upload to S3. Console app auth skeleton connected to real data.

**Docs:** `02_System_Architecture`, `03_Database_Design`, `04_Backend_Architecture`, `05_API_Specification`, `07_Security_Architecture` (auth sections)

### What we already have

- `backend/app/` directory structure (core, auth, errors, models, schemas, repositories, services, storage, routers)
- `Project`, `File`, `StorageConfig`, and `StorageMigration` SQLAlchemy models
- `TenantContext`, `authenticate_request`, `require_scope` wired up
- S3 storage provider and resolver with SSE support (`_sse_params()`, `sse_enabled` per config row)
- Storage config service, repository, and router (`GET /storage`, `PATCH /storage`, `POST /storage/verify`, `PATCH /storage/sse`)
- Health router
- Initial Alembic migration applied (tables: `projects`, `files`, `storage_configs`, `storage_migrations`)
- Docker Compose: PostgreSQL, Redis, MinIO, NATS, ClamAV
- IAM: auth, API key plugin, OAuth client
- Frontend: login → callback → onboarding wizard scaffold (multi-step: create org → get API key → install SDK)
- Console clean architecture: DI container, AppSidebar, projects table (list + grid view, row selection, create/delete modals)
- Project Settings → Storage tab: provider selector, dynamic BYOB credential form, SSE toggle (MinIO/RustFS)

### Deliverables

**Database**
- Run initial Alembic migration (`backend/migrations/alembic/versions/001_initial_schema.py`)
- Tables: `projects`, `files`, `storage_configs`, `storage_migrations`, `outbox_messages`, `upload_sessions`
- `organizations`, `users`, `api_keys` — **not here**, they live in IAM's Prisma DB

**Project API**
- `POST /v1/projects` — create project. Body includes `storage_mode` (managed | byob) and `storage_provider` (s3 | azure_blob | gcs | minio | r2 | rustfs). For Phase 1 `byob` accepts the fields but BYOB full configuration is enforced from Phase 7 onward.
- `GET /v1/projects` — list projects in org
- `GET /v1/projects/{id}` — get project
- `PATCH /v1/projects/{id}` — update name/description
- `DELETE /v1/projects/{id}` — soft delete

**Storage Config API (foundation — full BYOB wiring in Phase 7)**
- `GET /v1/projects/{id}/storage` — return current storage config (non-sensitive fields: mode, provider, region, bucket, endpoint_url, sse_enabled)
- `PATCH /v1/projects/{id}/storage` — save BYOB credentials (encrypted); sets status to `pending_verification`
- `POST /v1/projects/{id}/storage/verify` — connectivity test: write + delete a probe object → `{ ok, latency_ms, error }`
- `PATCH /v1/projects/{id}/storage/sse` — toggle SSE (MinIO/RustFS only; S3/R2/Azure/GCS default to always-on)
- A `StorageConfig` row is created automatically when a project is created (managed S3 defaults; `sse_enabled` defaults true for S3/R2/Azure/GCS, false for MinIO/RustFS)

**File Upload & Download**
- `POST /v1/projects/{id}/files/upload` — single file, multipart/form-data, writes to S3, creates file record (`status=ready`)
- `GET /v1/projects/{id}/files` — list files (pagination, filter by mime_type/status)
- `GET /v1/projects/{id}/files/{file_id}` — get file metadata
- `GET /v1/projects/{id}/files/{file_id}/download` — redirect to 15-min presigned S3 URL
- `DELETE /v1/projects/{id}/files/{file_id}` — soft delete (`deleted_at` set)

**Health**
- `GET /health/live` — always 200
- `GET /health/ready` — checks DB + Redis

**Console App — Auth Connected**
- Login → callback → `getServerSession()` reads real session
- First-login onboarding: create org (IAM), generate API key, view dashboard
- `/dashboard` shows real project list from backend API
- Session cookie set correctly; `activeOrganizationId` propagated

**Dev Environment**
- `just dev` starts all containers
- `just migrate` runs Alembic
- `just seed-dev` seeds a project with a known `organization_id`
- `just backend` hot-reloads the FastAPI server

### Exit Criteria

- `curl -H "Authorization: Bearer fn_live_..." -F file=@test.pdf http://localhost:8000/v1/projects/{id}/files/upload` → file in MinIO, record in DB
- Presigned download URL works
- New user signs up via console → creates org → can see empty project list

---

## PHASE 2 — Processing & Events

**Duration:** Weeks 4–8
**Goal:** Files move through a processing pipeline after upload. Webhooks fire on state changes. Multipart upload works.

**Docs:** `11_Event_Architecture`, `13_Processing_Pipelines`, `05_API_Specification`

### Deliverables

**NATS JetStream + Transactional Outbox**
- JetStream stream: `FILENEST_EVENTS`, subjects `filenest.>`
- `outbox_messages` table + `OutboxWorker`: polls pending rows → publishes to NATS → marks published
- `TransactionalOutboxPublisher.publish()` called inside the same DB transaction as the business operation
- Consumer groups: `processing-workers`, `webhook-workers`

**Multipart Upload**
- `POST /v1/projects/{id}/files/upload/multipart/start` — creates upload session, returns `upload_id`
- `GET /v1/projects/{id}/files/upload/multipart/{upload_id}/part-url?part={n}` — returns presigned S3 part URL
- `POST /v1/projects/{id}/files/upload/multipart/{upload_id}/complete` — assembles parts, triggers processing
- `DELETE /v1/projects/{id}/files/upload/multipart/{upload_id}` — abort, cleans up S3 parts
- File status during upload: `uploading` → `processing` → `ready` | `failed` | `quarantined`

**Processing Pipeline (parallel first-pass stages)**
- `ProcessingWorker`: NATS pull subscriber on `filenest.*.*.file.uploaded`, semaphore (20 concurrent)
- `VirusScanStage`: ClamAV via clamd TCP. On `FOUND` → `status=quarantined`, emit `file.quarantined`
- `MimeValidationStage`: python-magic byte-sniff vs declared Content-Type; mismatch → `status=failed`
- `ClassificationStage`: extension → category map (`document`, `image`, `video`, `audio`, `archive`, `other`)
- After all stages pass → `status=ready`, emit `file.ready`

**File Versioning**
- Upload to existing `storage_key` path → creates new `file_versions` row, bumps `version_count`
- `GET /v1/projects/{id}/files/{file_id}/versions` — list versions with size, created_at
- `GET /v1/projects/{id}/files/{file_id}/versions/{version_id}/download` — signed URL for specific version
- `POST /v1/projects/{id}/files/{file_id}/versions/{version_id}/restore` — makes version the current one

**Webhook Delivery**
- `POST /v1/projects/{id}/webhooks` — register endpoint (url, events[], signing_secret auto-generated)
- `GET /v1/projects/{id}/webhooks`, `PUT /v1/projects/{id}/webhooks/{id}`, `DELETE /v1/projects/{id}/webhooks/{id}`
- `GET /v1/projects/{id}/webhooks/{id}/deliveries` — delivery history with status + response code
- `WebhookWorker`: NATS consumer → signs payload HMAC-SHA256 → POST to customer URL
- Retry: 3 attempts, exponential backoff (30s → 60s → 120s)
- `webhook_deliveries` table: tracks delivery attempts, response codes, response body (first 2 KB)

**Audit Logging (Core)**
- `audit_logs` table — append-only, no UPDATE/DELETE
- Writes on: upload, download, delete, version restore, webhook create/delete
- Always in the same DB transaction as the business operation

### Exit Criteria

- Upload EICAR test virus → file status becomes `quarantined` within 10 seconds
- Upload 200 MB file via multipart → completes, file accessible
- Webhook fires within 5 seconds of `file.ready`
- File versioning: upload same key twice → two versions retrievable independently

---

## PHASE 3 — Metadata, Search & Folders

**Duration:** Weeks 7–12 (overlaps with Phases 4 and 5)
**Goal:** Files are searchable. Custom metadata schemas work. OCR extracts text from PDFs. Folders organize files.

**Docs:** `10_Search_Architecture`, `03_Database_Design` (metadata tables), `05_API_Specification`, `13_Processing_Pipelines` (OCR + indexing)

### Deliverables

**Custom Metadata**
- `metadata_schemas` table: project-scoped JSON Schema definitions
- `POST /v1/projects/{id}/metadata-schemas` — define/update active schema
- `GET /v1/projects/{id}/metadata-schemas` — list schemas (with active flag)
- File `metadata` JSONB column: stores per-file key-value pairs
- `PUT /v1/projects/{id}/files/{file_id}/metadata` — update metadata, validated against active schema if enforce_schema=true
- `MetadataValidationError` raised on schema violation (HTTP 422 with field-level errors)

**Folder Hierarchy**
- `folders` table: `id`, `project_id`, `parent_folder_id`, `name`, `path` (materialized), `created_at`
- `POST /v1/projects/{id}/folders` — create folder (with optional parent)
- `GET /v1/projects/{id}/folders` — list top-level + subtree
- `GET /v1/projects/{id}/folders/{folder_id}/files` — list files in folder
- `POST /v1/projects/{id}/files/{file_id}/move` — move file to folder (updates `folder_id`)
- `DELETE /v1/projects/{id}/folders/{folder_id}` — soft delete (requires folder to be empty)

**Tags**
- `tags` text[] column on `files`
- `PUT /v1/projects/{id}/files/{file_id}/tags` — replace tag set
- `POST /v1/projects/{id}/files/{file_id}/tags` — add tags
- Tags filterable in file list + search

**OpenSearch Integration**
- One index per project: `filenest-{project_id}`
- Mapping: `filename`, `mime_type`, `size`, `tags`, `metadata.*`, `ocr_text`, `category`, `folder_id`, `created_at`, `status`
- `IndexingStage` (replaces Phase 2 stub): indexes on `file.ready`
- Delete from index on `file.deleted`

**OCR Stage**
- `OCRStage`: PyMuPDF text extraction for PDFs (fast path). pytesseract fallback for scanned images.
- Extracted text stored in `ocr_texts` table (separate from `files` — avoids large column on main table)
- OCR text indexed into OpenSearch `ocr_text` field
- Stage added to pipeline after `MimeValidationStage` (sequential, PDF/image only)

**Search API**
- `POST /v1/projects/{id}/search` — body: `{ q, filters, tags, date_from, date_to, size_min, size_max, folder_id, sort_by, sort_order, limit, offset }`
- Response: `{ hits: [{ file_id, filename, score, highlights }], total, facets }`
- `GET /v1/projects/{id}/files` — list with same filter params (no full-text, uses DB not OpenSearch)
- Facets: `mime_type`, `category`, `tags` counts

### Exit Criteria

- Upload a PDF containing the word "discharge" → `POST /search { q: "discharge" }` → file in results with highlight
- Custom metadata schema defined → upload file with missing required field → HTTP 422 with field path
- Files organized in folders → `GET /folders/{id}/files` returns correct subset
- Search across `tags`, `metadata.patientId`, and `ocr_text` in a single query

---

## PHASE 4 — Console App

**Duration:** Weeks 9–16 (overlaps with Phases 3 and 5)
**Goal:** Developers and org admins can manage everything through a UI without touching the raw API.

**Docs:** `24_Admin_Dashboard`, `06_SDK_Specification` (React SDK usage)

### Deliverables

**Layout & Navigation**
- `(app)/` route group with session + active org guard
- `AppSidebar`: Projects, Dashboard, Org settings (Team, Usage)
- `OrgSwitcher`: switch between orgs (multi-org users)
- `ThemeSwitcher`: light/dark

**Dashboard — `/dashboard`**
- Storage used (GB), API requests (30d), files uploaded (30d), processing jobs (30d) — from usage API
- Recent files list (last 10)
- Quick actions: Upload file, Create project, Generate API key

**Projects — `/projects`**
- List all projects in active org (name, file count, storage used, created date)
- Create project modal (name, slug auto-generated, storage mode: Managed only for now)

**File Explorer — `/projects/{id}/files`**
- Folder tree sidebar (collapsible)
- File list: name, type icon, size, status badge, modified date
- Upload via `<FileUpload>` component (drag-and-drop, progress bar, file type filtering)
- Download selected file(s)
- Delete with confirmation
- Rename file
- Move to folder
- View metadata panel (side drawer with all metadata key-values)
- Search bar (full-text + tag filter) — calls `/v1/projects/{id}/search`
- Pagination

**API Keys — `/projects/{id}/api-keys`**
- List keys (prefix `fn_live_...`, name, scopes, last used, expires)
- Create key: name, scopes (checkboxes), optional expiry → show full key once in modal
- Revoke key with confirmation
- All key CRUD goes through IAM API (not FileNest backend)

**Webhooks — `/projects/{id}/webhooks`**
- List configured webhooks (URL, events, status: active/failing/disabled)
- Add webhook: URL + event checkboxes + auto-generated signing secret (show once)
- Enable/disable toggle
- Delivery history table per webhook (timestamp, event, status, response code)
- "Test" button — sends a `ping` event

**Project Settings — `/projects/{id}/settings`**
- General tab: name, description
- Storage tab: current mode shown ("Managed — FileNest S3"). "Switch to custom storage" button shown but disabled with "Coming in Phase 7"
- Processing tab: toggle stages (virus scan always on; OCR optional)

**Team — `/org/team`**
- Invite member by email (calls IAM invite endpoint)
- Member list: avatar, name, email, role badge
- Role assignment: Owner / Admin / Member / Viewer
- Remove member with confirmation

**Usage — `/org/usage`**
- Storage: used / limit GB progress bar
- API requests: used / limit per month
- Processing jobs: used / limit per month
- Breakdown by project (table)

**Onboarding Wizard** (shown on first login, no active org)
1. Create org: confirm name, set slug
2. Create first project: name + slug
3. Generate first API key: scope preselected, show once
4. First upload: drag-and-drop with live progress

### Exit Criteria

- New user signs up → completes onboarding → uploads a file → downloads it — all within the UI, no terminal
- Admin creates API key with specific scopes → key works in `curl`
- Team member invited by email → accepts → sees project with correct permissions
- Webhook configured → file uploaded → delivery visible in history table within 10 seconds

---

## PHASE 5 — SDKs & Developer Experience

**Duration:** Weeks 13–18 (overlaps with Phase 4)
**Goal:** External developers can integrate FileNest in under 30 minutes. Docs live. SDKs published. Example applications demonstrate every SDK feature in isolation.

**Docs:** `06_SDK_Specification`

### Deliverables

**@filenest/node** (npm)
- `FileNest` client class with `apiKey`, `projectId`, base URL config
- `files.upload(data, options)` — handles single (<5 MB) and multipart (>5 MB) automatically
- `files.download(fileId)` — returns Node.js readable stream
- `files.list(filters)`, `files.get(fileId)`, `files.delete(fileId)`
- `files.getDownloadUrl(fileId, { ttl })` — returns presigned URL
- `files.updateMetadata(fileId, metadata)`
- `search.query({ q, filters, tags, facets })`
- `webhooks.verify(rawBody, signatureHeader, secret)` — HMAC-SHA256 verification
- TypeScript types for all request/response shapes
- Published to npm: `@filenest/node`

**@filenest/react** (npm)
- `<FileNestProvider tokenEndpoint="/api/filenest-token" projectId={...}>`
- `<FileUpload>` — drag-and-drop, progress bars, file type/size restrictions, `onComplete`, `onError`
- `<FileExplorer>` — browse folders, search, upload, download, delete
- `<FilePreview>` — inline image/PDF preview (basic; full previews in Phase 7)
- `useUpload()` — programmatic upload with progress state
- `useFiles(filters)` — TanStack Query-backed list with pagination
- `useSearch()` — debounced full-text + faceted search
- `useFile(fileId)` — single file detail
- `useFolder(folderId)` — folder navigation with breadcrumbs
- Published to npm: `@filenest/react`

**@filenest/nextjs** (npm)
- `filenestServer({ apiKey, projectId })` — server-side client for server components + actions
- `createUploadToken({ constraints, metadata, expiresIn })` — for the token endpoint
- `verifyWebhookSignature(body, signature, secret)` + `parseWebhookEvent(body)`
- Published to npm: `@filenest/nextjs`

**filenest** (PyPI)
- `FileNestClient` and `AsyncFileNestClient` with same surface as Node SDK
- `files.upload()`, `files.download()`, `files.list()`, `files.delete()`
- `search.query()`
- `webhooks.verify(body, signature, secret)`
- Django and FastAPI integration helpers
- Published to PyPI: `filenest`

**API Documentation**
- OpenAPI 3.1 spec generated from FastAPI routes (already at `GET /docs` in dev)
- Hosted docs site (Mintlify or Stoplight): `docs.filenest.io`
- Getting started guide: 5 minutes to first upload
- Code examples in Node.js, Python, curl for every endpoint
- SDK quickstart pages with copy-paste snippets
- Webhook guide with signature verification examples

**Example Applications** (built in parallel with the SDKs, lives in `examples/`)

One standalone app per SDK. Each app dedicates a separate page or route to a single SDK feature so the implementation is immediately readable in isolation. Every page shows the running UI alongside the relevant source code snippet (like a mini playground).

```
examples/
├── node-sdk/          # Plain Node.js + Express — demonstrates @filenest/node
├── react-sdk/         # Vite + React — demonstrates @filenest/react components and hooks
├── nextjs-sdk/        # Next.js App Router — demonstrates @filenest/nextjs server utilities
└── python-sdk/        # FastAPI app — demonstrates filenest Python SDK
```

_`examples/node-sdk/`_ — `@filenest/node` (Express, no frontend framework)

| Route | Feature demonstrated |
|-------|---------------------|
| `GET /` | Index — links to all examples |
| `POST /upload/single` | Single file upload (`files.upload` < 5 MB) |
| `POST /upload/multipart` | Large file upload (`files.upload` auto-multipart > 5 MB) |
| `GET /files` | List files with status + MIME filter (`files.list`) |
| `GET /files/:id` | Get file metadata (`files.get`) |
| `GET /files/:id/download` | Presigned download URL (`files.getDownloadUrl`) |
| `DELETE /files/:id` | Delete file (`files.delete`) |
| `PUT /files/:id/metadata` | Update metadata (`files.updateMetadata`) |
| `PUT /files/:id/tags` | Replace tag set |
| `POST /files/:id/tags` | Add tags |
| `POST /search` | Full-text + faceted search (`search.query`) |
| `POST /webhooks/receive` | Receive + verify a webhook delivery (`webhooks.verify`) |

_`examples/react-sdk/`_ — `@filenest/react` (Vite + React, one route per component/hook)

| Route | Feature demonstrated |
|-------|---------------------|
| `/` | Index — links to all examples |
| `/upload/dropzone` | `<FileUpload variant="dropzone">` drag-and-drop with progress |
| `/upload/button` | `<FileUpload variant="button">` click-to-upload |
| `/upload/programmatic` | `useUpload()` — manual trigger, per-file progress state, retry |
| `/explorer` | `<FileExplorer>` — full folder browse, search, upload, download |
| `/preview/:fileId` | `<FilePreview>` — inline image/PDF preview |
| `/viewer/:fileId` | `<FileViewer>` — full-page document viewer |
| `/files` | `useFiles(filters)` — paginated list with status + MIME filter controls |
| `/search` | `useSearch()` — debounced input, facet sidebar, highlighted results |
| `/file/:fileId` | `useFile(fileId)` — single file detail card with live status polling |
| `/folder/:folderId` | `useFolder()` — breadcrumb navigation, subfolder list |

Each page is split into two panes: left = running demo, right = the full source file with syntax highlighting.

_`examples/nextjs-sdk/`_ — `@filenest/nextjs` (Next.js 16 App Router)

| Route | Feature demonstrated |
|-------|---------------------|
| `/` | Index |
| `/server-component` | RSC fetching a file list with `filenestServer().files.list()` |
| `/server-action` | Server action uploading a file with `filenestServer().files.upload()` |
| `/upload-token` | Token endpoint (`/api/filenest-token`) + `<FileUpload>` consuming it |
| `/webhooks` | `/api/webhooks/filenest` — `verifyWebhookSignature` + `parseWebhookEvent` |
| `/search` | Server component calling `filenestServer().search.query()` |

_`examples/python-sdk/`_ — `filenest` PyPI (FastAPI app, one router per feature group)

| Route | Feature demonstrated |
|-------|---------------------|
| `GET /` | Index — links to all examples |
| `POST /upload` | Single file upload (`AsyncFileNestClient.files.upload`) |
| `GET /files` | List files with filters |
| `GET /files/{id}/download-url` | Presigned URL (`files.getDownloadUrl`) |
| `DELETE /files/{id}` | Delete file |
| `PUT /files/{id}/metadata` | Update metadata |
| `POST /search` | Full-text search (`search.query`) |
| `POST /webhooks/receive` | Webhook receipt + `webhooks.verify` |
| `GET /django-example` | Inline Django view snippet (rendered as a code block) |

Each example app ships with:
- A `README.md` — one-command setup (`cp .env.example .env` → `pnpm dev` / `uvicorn main:app`)
- `.env.example` — `FILENEST_API_KEY`, `FILENEST_PROJECT_ID`, `FILENEST_API_URL`
- No authentication, no database — purely FileNest SDK calls so there is nothing else to set up

### Exit Criteria

- Node SDK: `new FileNest({ apiKey, projectId }).files.upload(buffer, { filename: "test.pdf" })` works
- React SDK: `<FileUpload>` in a bare Next.js app uploads to the right project
- Python SDK: `AsyncFileNestClient().files.upload(...)` works inside a FastAPI endpoint
- Webhook: `verifyWebhookSignature` returns `true` on a real delivery, `false` on tampered payload
- Docs site live with working "Try it" examples
- All four example apps start with a single command and each individual feature page works end-to-end against a real FileNest project

---

## PHASE 6 — Production Infrastructure

**Duration:** Weeks 16–23
**Goal:** Observable, rate-limited, Kubernetes-deployed platform ready for production traffic.

**Docs:** `14_Kubernetes_Deployment`, `15_Observability`, `16_Rate_Limiting`, `17_Usage_Metering`, `22_Email_Notifications`, `20_Background_Jobs`

### Deliverables

**Observability**
- OTel SDK auto-instrumentation: FastAPI, SQLAlchemy, Redis, httpx
- OTel Collector → Tempo (traces), Prometheus (metrics), Loki (logs)
- structlog JSON logging with `request_id` + `trace_id` on every line
- 15+ Prometheus metrics: upload count/duration, processing latency, search latency, webhook delivery rate, auth failures, queue depth
- Grafana dashboards: API Overview, Processing Queue, Storage Usage
- Alerting: API down, error rate > 5%, DB connections exhausted, virus scan unavailable, P95 latency > 2s

**Rate Limiting**
- Token bucket via Redis Lua atomic script (no race condition)
- Per-org limits (tiers configurable via env): Starter 100/min, Professional 1000/min, Enterprise 10000/min
- Per-key limits: live 500/min, test 200/min
- Enforces stricter of org vs key
- `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers on every response
- HTTP 429 with `{ error: { code: "rate_limited", retry_after: N, limited_by: "org"|"key" } }`

**Usage Metering**
- Redis counters per org per month: API calls, upload bytes, download bytes, processing jobs, searches
- `UsageFlushJob`: Redis → PostgreSQL `usage_snapshots` every 5 minutes
- `StorageCalculationJob`: `SUM(size)` from files table hourly per project
- `GET /v1/organizations/{id}/usage` — returns per-metric used/limit breakdown
- Enforce storage + processing limits: HTTP 402 on breach with `{ exceeded: "storage"|"requests" }`

**Email Notifications (Core)**
- AWS SES (primary) + SendGrid (fallback)
- Core notifications: virus detected, API key revoked, usage at 95%, storage limit reached
- Jinja2 templates (HTML + plain text)
- `NotificationWorker`: NATS pull subscriber → render → SES/SendGrid

**Background Jobs**
- `UploadSessionCleanupJob`: aborts multipart uploads > 24h, marks orphaned file records `failed` (every 30 min)
- `ProcessingStuckDetectionJob`: re-queues jobs stuck > 30 min (every 5 min)
- Runs as Kubernetes CronJobs using the same backend image: `python -m app.jobs <job_name>`

**Kubernetes (EKS)**
- Node pools: api (c5.xlarge, 5–20), workers (c5.2xlarge, 5–50), data (r5.2xlarge, 3 fixed), search (r5.2xlarge, 3–6)
- 3 deployments from one image: `filenest-api`, `processing-worker`, `webhook-worker`
- HPA: CPU-based for API; KEDA (NATS lag) for processing workers
- External Secrets Operator + AWS Secrets Manager for all credentials
- IRSA per deployment (least privilege)
- NetworkPolicy: default-deny, explicit allowlists
- RDS Multi-AZ, daily Velero backup
- `GET /health/ready` wired to readiness probe

**CI/CD**
- GitHub Actions: test → lint → build → push ECR → `helm upgrade --atomic`
- Alembic migration as Helm pre-install/pre-upgrade Job
- Rollback: `helm rollback` on failed health check

### Exit Criteria

- 100 concurrent uploads with no errors and stable P99 latency
- Rate limit headers on every response; 429 fires correctly on breach
- Prometheus metrics visible in Grafana; alert fires when a service is killed
- Kubernetes rolling deploy with zero downtime
- Usage endpoint returns correct byte counts after 50 uploads

---

## PHASE 7 — Advanced Features

**Duration:** Weeks 20–30 (overlaps with Phase 6)
**Goal:** Full product surface — all storage providers, BYOB, previews, sharing, bulk operations, semantic search.

**Docs:** `12_Storage_Abstraction`, `19_Sharing_System`, `21_Preview_Generation`, `23_Bulk_Operations`, `20_Background_Jobs`

### Deliverables

**Storage Abstraction — All Providers**
- `StorageProvider` Protocol fully implemented for: AWS S3, Azure Blob, GCS, MinIO, Cloudflare R2, RustFS (Rust-native S3-compatible)
- `StorageResolver.build_provider(storage_config)` reads mode + provider from the `storage_configs` row to dispatch to the correct implementation
- All providers expose: `upload`, `download_stream`, `delete`, `copy`, `generate_presigned_upload_url`, `generate_presigned_download_url`, `delete_object`, `object_exists`, `create_bucket`

**BYOB (Bring Your Own Storage)**
- `storage_mode`: `managed` (default — FileNest-managed bucket) or `byob` (customer-supplied endpoint)
- BYOB provider options: S3 (static keys), MinIO, RustFS, R2, Azure Blob, GCS
- `PATCH /v1/projects/{id}/storage` — save BYOB credentials (encrypted); sets status to `pending_verification` _(foundation endpoint built in Phase 1)_
- `POST /v1/projects/{id}/storage/verify` — write + delete a test object; returns `{ ok, latency_ms, error }` _(foundation built in Phase 1)_
- `PATCH /v1/projects/{id}/storage/sse` — toggle SSE (MinIO / RustFS only; S3/R2/Azure/GCS are always-on) _(built in Phase 1)_
- `GET /v1/projects/{id}/storage` — plaintext fields only (`mode`, `provider`, `endpoint_url`, `bucket_name`, `region`); credentials never returned _(built in Phase 1)_
- Credential encryption: AES-256-GCM with per-record key derivation (HKDF) in `backend/app/core/crypto.py`
- `STORAGE_CREDENTIAL_KEY` env var — loaded at startup, never logged

**BYOB Console UI**
- Project Settings → Storage tab: provider selector + dynamic form per provider _(foundation form built in Phase 1; Phase 7 completes verification flow and migration button)_
- "Test connection" button → calls verify endpoint → shows ✓ / ✗ + latency
- Save only enabled after successful verification
- Storage migration button: switch provider → background migration job

**Storage Migration Worker**
- `POST /v1/admin/projects/{id}/storage/migrate` — triggers migration to new provider config
- Dry run: returns file count + estimated duration
- Worker: stream each file from source → upload to target → verify size → update `storage_key`
- `GET /v1/admin/projects/{id}/storage/migrations/{id}` — progress: completed/total/errors/status

**Preview Generation**
- `PreviewGenerationStage` added to processing pipeline (sequential, after OCR)
- PDF → PyMuPDF → inline preview PNG per page
- Images → PIL → resized to 2048px max, converted to WebP
- Office files (DOCX, XLSX, PPTX) → Gotenberg (LibreOffice wrapper) → PDF → preview
- Video → ffmpeg poster frame at 5 seconds → WebP
- Audio → soundfile + matplotlib waveform → WebP
- `GET /v1/projects/{id}/files/{file_id}/preview` — returns `{ preview_url, poster_url, page_count, preview_type }`
- `<FilePreview>` React component: image lightbox, PDF viewer (PDF.js), Office preview (embedded PDF), video player

**Sharing System**
- `POST /v1/projects/{id}/files/{file_id}/share-links` — create link (expiry, max_downloads, optional password, allowed_email_domain)
- Public URL: `https://share.filenest.io/s/{token}` (32-byte URL-safe token)
- Password: bcrypt hashed, 10 attempts/hr then locked
- `GET /s/{token}` — public share page (no auth required, shows preview)
- `POST /s/{token}/access` — verify password → return 15-min access token
- `GET /s/{token}/download` — stream via signed URL (counts against max_downloads)
- `GET /v1/projects/{id}/files/{file_id}/share-links` — list active links
- `DELETE /v1/share-links/{link_id}` — revoke link

**Bulk Operations**
- All bulk ops async: `202 Accepted` with `{ job_id }`
- `BulkJobWorker`: NATS pull subscriber, `FOR UPDATE SKIP LOCKED`
- `POST /v1/projects/{id}/bulk/delete` — `{ file_ids[] }` → deletes each; skips if not found
- `POST /v1/projects/{id}/bulk/move` — `{ file_ids[], folder_id }` → moves to folder
- `POST /v1/projects/{id}/bulk/tag` — `{ file_ids[], tags[], mode: "add"|"replace" }`
- `POST /v1/projects/{id}/bulk/download` — streams all files into zip → signed URL (1-hour expiry)
- `POST /v1/projects/{id}/bulk/metadata` — `{ file_ids[], metadata }` → updates metadata on each
- `POST /v1/projects/{id}/bulk/reprocess` — re-queues processing for selected files
- `GET /v1/bulk-jobs/{job_id}` — status + per-file results (`completed`, `skipped`, `failed`)

**Semantic Search (Embeddings)**
- `EmbeddingStage`: generates embeddings via OpenAI `text-embedding-3-small` on OCR text + metadata
- Embeddings stored in OpenSearch `knn_vector` field
- `POST /v1/projects/{id}/search` extended: `mode: "full_text" | "semantic" | "hybrid"`
- Hybrid: BM25 + cosine similarity with RRF fusion

**Full Email Notifications**
- All notification types from `22_Email_Notifications`: upload complete, processing failed, webhook failing, storage approaching limit, share link accessed, new team member, API key expiring, etc.
- Per-user notification preferences (email / in-app / both / none per event type)
- In-app notification bell: `GET /v1/notifications`, `POST /v1/notifications/{id}/read`, `POST /v1/notifications/read-all`
- Daily digest option: batches notifications into a single summary email

**Full Background Jobs**
- `RetentionEnforcementJob`: deletes/archives files past their `retain_until` date (daily, skips legal-held files — those are compliance v2)
- `AuditLogArchivalJob`: gzip JSONL → S3 Glacier for logs older than 90 days (monthly)
- `ShareLinkExpiryCleanupJob`: deactivates expired + exhausted share links (hourly)
- `StorageUsageRecalculationJob`: full recalculation from DB when Redis counters drift (weekly)

### Exit Criteria

- Configure a project with a self-hosted MinIO or RustFS endpoint → connection verified → upload a file → it lands in the customer's bucket, not FileNest's
- Upload a DOCX → preview available as PDF in the console UI
- Share a file publicly with a password → recipient downloads it without an account
- Bulk delete 500 files in one API call → job completes, status shows per-file results
- Semantic search: "find all invoices from Q1 2026" returns relevant results ranked by similarity
- All credentials in DB are AES-256-GCM ciphertext — plaintext never appears outside application memory

---

## ═══════════════════════════════════════
## v1.0 COMPLETE — End of Phase 7
## ═══════════════════════════════════════

At v1.0, FileNest is a full file infrastructure platform:
- Upload → process → store → search → share via API, SDK, or console
- Any S3-compatible storage backend, including customer-supplied (BYOB)
- Virus scanning on every file
- OCR + full-text search + semantic search
- File versioning, folders, tags, custom metadata
- Webhooks with HMAC signing and retry
- Sharing with optional password + expiry
- Bulk operations
- Preview generation for PDFs, images, Office files, video
- Observable (OTel traces, Prometheus metrics, structured logs)
- Rate-limited per org and per key
- Deployed on Kubernetes with HPA and zero-downtime deploys

**Explicitly deferred to v2.0 — Compliance Pack:**

FileNest stores any kind of file. Compliance requirements are domain-specific and layered on top of the core platform. These are deferred to v2.0:

- **Regulatory compliance per domain** — e.g. healthcare (HIPAA, FHIR), finance (PCI-DSS, SOX), legal (chain-of-custody), government (FedRAMP). Each domain pack adds the specific audit requirements, data handling rules, and certification controls for that industry.
- **WORM** — immutable S3 Object Lock for write-once records
- **Legal hold** — block delete/move on flagged files pending litigation or audit
- **Retention enforcement** — policy-driven auto-delete or auto-archive after a defined period
- **Customer-managed KMS (BYOK)** — envelope encryption with customer-controlled keys
- **Sensitive data detection** — scan file content for regulated data patterns (PII, PHI, PAN, etc.) and apply policies based on what's found

The compliance modules are already scaffolded in the codebase with clean interfaces. Adding them in v2.0 requires implementing the service logic, not refactoring existing code.

---

## Phase → Component Matrix

| Component | Introduced | Extended |
|-----------|-----------|---------|
| PostgreSQL schema | Phase 1 | Every phase |
| S3 storage (managed) | Phase 1 | Phase 7 (all providers + BYOB) |
| FastAPI routes | Phase 1 | Every phase |
| NATS + transactional outbox | Phase 2 | Phase 6 (observability), Phase 7 (bulk) |
| Processing pipeline | Phase 2 | Phase 3 (OCR), Phase 7 (previews, embeddings) |
| File versioning | Phase 2 | — |
| Webhooks | Phase 2 | Phase 6 (retry + metrics) |
| Audit logging | Phase 2 | Phase 6 (full observability), Phase 7 (archival) |
| Custom metadata | Phase 3 | Phase 7 (bulk metadata update) |
| Folder hierarchy | Phase 3 | — |
| Tags | Phase 3 | Phase 7 (bulk tag) |
| OpenSearch + indexing | Phase 3 | Phase 7 (knn_vector, semantic search) |
| OCR stage | Phase 3 | — |
| Console App | Phase 4 | Phase 7 (previews, BYOB UI, notifications) |
| @filenest/node | Phase 5 | Phase 7 (bulk ops) |
| @filenest/react | Phase 5 | Phase 7 (previews, sharing) |
| @filenest/nextjs | Phase 5 | — |
| filenest Python SDK | Phase 5 | — |
| Example applications (`examples/`) | Phase 5 | Phase 7 (preview + sharing + bulk examples added) |
| Observability (OTel + Grafana) | Phase 6 | Phase 7 (audit archival dashboard) |
| Rate limiting | Phase 6 | — |
| Usage metering | Phase 6 | — |
| Email notifications (core) | Phase 6 | Phase 7 (full suite) |
| Background jobs (core) | Phase 6 | Phase 7 (full suite) |
| Kubernetes + Helm | Phase 6 | Phase 7 (Gotenberg pod) |
| CI/CD | Phase 6 | — |
| `StorageConfig` + `StorageMigration` models | Phase 1 | Phase 7 (BYOB credentials wired) |
| Storage provider selection at project creation | Phase 1 | Phase 7 (full BYOB enforcement) |
| All storage providers | Phase 7 | — |
| BYOB dual-mode (full credential flow) | Phase 7 | — |
| Credential encryption | Phase 7 | v2.0 (KMS envelope) |
| Storage migration worker | Phase 7 | — |
| Preview generation | Phase 7 | — |
| Sharing system | Phase 7 | — |
| Bulk operations | Phase 7 | — |
| Semantic search | Phase 7 | — |
| In-app notifications | Phase 7 | — |
| Retention job (basic) | Phase 7 | v2.0 (compliance-aware) |
| Audit log archival | Phase 7 | v2.0 (Glacier + tamper-evident) |

---

## Dependency Graph

```
Phase 1 — Foundation
  └─→ Phase 2 — Processing & Events
        ├─→ Phase 3 — Metadata, Search & Folders  ──┐
        ├─→ Phase 4 — Console App                  ──┤ (parallel)
        └─→ Phase 5 — SDKs                         ──┘
              │
              ▼
        Phase 6 — Production Infrastructure
              │
              └─→ Phase 7 — Advanced Features
                        │
                        ▼
                   [ v1.0 COMPLETE ]
                        │
                        ▼
                   v2.0 — Compliance Pack
```

