# FileNest v1.0 — Implementation Roadmap

**Version:** 1.0.0
**Status:** Active Planning
**Last Updated:** 2026-06-17

---

## Overview

This roadmap organizes all 24 engineering documents into a phase-by-phase build order. The primary goal is shipping a working MVP as fast as possible, then layering compliance, advanced features, and production hardening in subsequent phases.

**Note on scope:** FileNest is a file infrastructure platform. AI products built on top of FileNest (SOAP note generation, audio transcription, conversation memory, etc.) are separate applications that use FileNest as their file backend. Those are out of scope for this roadmap.

**Two tracks:**
- **MVP (Phases 1–5):** Core file infrastructure that developers can actually integrate and use. No compliance, no multi-cloud. Working product.
- **Production (Phases 6–8):** Compliance packs, full observability, advanced features, multi-cloud storage.

### Pre-existing dependency: IAM

User authentication and **API key lifecycle** are handled by **the IAM** (`iam/`) — a BetterAuth service that acts as an OAuth 2.1 / OIDC server. This is **not built as part of this roadmap**; it already exists and only needs minor config tweaks before the console app can register as an OAuth client.

The IAM's `apiKey` plugin (prefix `fn_`) manages all API key creation, listing, and revocation. The FastAPI backend verifies incoming `fn_live_` / `fn_test_` keys by calling `POST /api/internal/verify-api-key` on the IAM — there is **no identity microservice** in the FileNest backend.

---

## Phase Overview Table

| Phase | Name | Track | Duration | Milestone |
|-------|------|--------|----------|-----------|
| 1 | Foundation | MVP | 5 weeks | Files upload to S3, auth works |
| 2 | Processing & Events | MVP | 5 weeks | Files are processed, webhooks fire |
| 3 | Metadata & Search | MVP | 5 weeks | Files are searchable |
| 4 | Console App | MVP | 6 weeks | Usable UI for managing projects |
| 5 | SDKs & Dev Experience | MVP | 4 weeks | **MVP COMPLETE** |
| 6 | Production Infrastructure | Production | 7 weeks | Kubernetes, observability, rate limiting |
| 7 | Advanced File Features | Production | 7 weeks | Sharing, previews, bulk ops, multi-cloud |
| 8 | Compliance & Domain Packs | Production | 10 weeks | **v1.0 COMPLETE** — HIPAA-ready, GDPR-compliant |

**With 4–6 engineers:** MVP ~20 weeks. Full platform ~38 weeks.
**With 6–10 engineers:** MVP ~12 weeks. Full platform ~26 weeks.

Phases 3, 4, and 5 run in parallel after Phase 2 completes. Phase 7 and 8 overlap.

---

## PHASE 1 — Foundation

**Duration:** Weeks 1–5
**Goal:** Working monorepo, database, auth system, and single-file upload to S3. The skeleton everything else is built on.

**Docs referenced:** `02_System_Architecture`, `03_Database_Design`, `04_Backend_Architecture`, `07_Security_Architecture` (auth sections only)

### Deliverables

**Infrastructure & Dev Environment**
- Monorepo structure (`/services`, `/packages`, `/infra`, `/dashboard`)
- Docker Compose: PostgreSQL, Redis, MinIO (local S3), NATS, ClamAV
- Alembic migration tooling wired up
- `.env` management with Pydantic Settings
- `make dev` one-command local startup

**Core Database Schema**
- `projects` table (with storage config, managed/byob mode)
- `files` table (core columns only: id, org_id, project_id, name, size, mime_type, storage_key, status, created_at)
- `outbox_messages` table (transactional outbox for NATS events)
- `upload_sessions` table (for multipart, used in Phase 2)

Note: `organizations`, `users`, and `api_keys` tables are **not in the FileNest DB** — they live in the IAM's BetterAuth/Prisma database. The FileNest DB references `organization_id` as a foreign key string only.

**Auth System**
- API keys (`fn_live_` / `fn_test_`) created and stored in the IAM (BetterAuth `apiKey` plugin)
- `authenticate_request` FastAPI dependency: extracts Bearer token, calls IAM's `/api/internal/verify-api-key` for API keys, or decodes JWT locally
- Key metadata (organizationId, projectId, scopes) stored in IAM's `metadata` field at key creation
- `require_scope()` dependency for FastAPI route guards

**Core File Upload/Download**
- `POST /v1/upload` — single file, multipart/form-data, writes to S3 (MinIO locally), creates file record with status=`ready`
- `GET /v1/files` — list files in project (pagination, basic filters)
- `GET /v1/files/{file_id}` — get file metadata
- `GET /v1/files/{file_id}/download` — redirect to presigned S3 URL (15-min TTL)
- `DELETE /v1/files/{file_id}` — soft delete (status=`deleted`)
- S3 storage provider only (no abstraction layer yet — that's Phase 7)

**Console App — Auth Skeleton (OAuth PKCE)**
- IAM config tweaks applied (org slug `filenest`, default role `member`, redirect `/dashboard`)
- OAuth client record created in IAM for the console app
- `(auth)/login/page.tsx` — generates PKCE state + verifier, redirects to IAM authorize endpoint
- `(auth)/callback/page.tsx` — validates state, calls `/api/auth/token`
- `api/auth/token/route.ts` — server-side code exchange with IAM, sets session cookie
- `getServerSession()` helper wired up for use in server components
- `GET /dashboard` — redirect to `/login` if no session; static placeholder page (org name + project list stub)

**Health Checks**
- `GET /health/live` — always 200
- `GET /health/ready` — checks DB connection + Redis

### Exit Criteria
- Developer can create an org, generate an API key, and upload a file via `curl`
- File appears in S3 (MinIO)
- Presigned download URL works
- Local `docker compose up` works for all team members

---

## PHASE 2 — Processing & Events

**Duration:** Weeks 5–10
**Goal:** Files move through a processing pipeline after upload. Webhooks fire on events. Multipart upload works.

**Docs referenced:** `11_Event_Architecture`, `13_Processing_Pipelines` (Phase 1+2 stages only), `05_API_Specification` (upload + webhook endpoints)

### Deliverables

**Multipart Upload**
- `POST /v1/upload/multipart/start` — creates upload session, returns `upload_id`
- `POST /v1/upload/multipart/{upload_id}/part` — returns presigned S3 part URL
- `POST /v1/upload/multipart/{upload_id}/complete` — assembles parts, triggers processing
- `DELETE /v1/upload/multipart/{upload_id}` — abort
- File status during upload: `pending` → `processing` → `ready` | `failed` | `quarantined`

**NATS JetStream**
- JetStream stream: `filenest` with subjects `filenest.files.*`, `filenest.internal.*`
- Transactional outbox: `outbox_events` table, `OutboxWorker` publishes rows to NATS
- Consumer groups: `processing-workers`, `webhook-workers`

**Processing Pipeline — Phase 1 (Parallel)**
- `ProcessingWorkerProcess`: NATS pull subscriber, semaphore (20 concurrent jobs)
- `VirusScanStage`: ClamAV via clamd TCP socket. On `FOUND` → status=`quarantined`, fire `file.quarantined` event
- `MimeValidationStage`: python-magic byte sniff vs declared Content-Type. Mismatch → status=`failed`

**Processing Pipeline — Phase 2 (Sequential stub)**
- Placeholder stages that pass through (OCR, PHI, PII — implemented in Phase 3 and Phase 8)
- `ClassificationStage`: metadata-based only (extension → category mapping)

**Processing Pipeline — Phase 3 (Parallel)**
- `IndexingStage`: sets status=`ready`, fires `file.ready` event

**Webhook Delivery**
- `POST /v1/webhooks` — create webhook endpoint (URL + events + secret)
- `GET /v1/webhooks`, `PUT /v1/webhooks/{id}`, `DELETE /v1/webhooks/{id}`
- `WebhookWorker`: NATS consumer, signs payload with HMAC-SHA256, POST to customer URL
- Retry: 3 attempts, exponential backoff (1s → 5s → 30s)
- `webhook_deliveries` table: tracks delivery attempts, response codes

**File Versioning**
- Upload to existing file key → creates new version record
- `GET /v1/files/{id}/versions` — list versions
- `GET /v1/files/{id}/versions/{version_id}/download`

### Exit Criteria
- Upload a file → it appears as `processing` → transitions to `ready` or `quarantined`
- Upload an EICAR test virus → file is quarantined
- Webhook fires within 5 seconds of file becoming `ready`
- Multipart upload of 100 MB file works end-to-end

---

## PHASE 3 — Metadata & Search

**Duration:** Weeks 9–14 (overlaps with Phases 4 and 5)
**Goal:** Files are searchable. Custom metadata schemas work. OCR extracts text from PDFs.

**Docs referenced:** `10_Search_Architecture`, `03_Database_Design` (metadata tables), `05_API_Specification` (search endpoints), `13_Processing_Pipelines` (OCR + indexing stages)

### Deliverables

**Custom Metadata**
- `metadata_schemas` table: org-scoped JSON Schema definitions
- `POST /v1/projects/{id}/metadata-schemas` — define schema
- `file_metadata` JSONB column: stores per-file metadata
- `PUT /v1/files/{id}/metadata` — update metadata, validated against schema

**Folder & Tag System**
- `folders` table: hierarchical (parent_folder_id), per-project
- `tags` array on files table
- `POST /v1/folders`, `GET /v1/folders/{id}/files`
- `PUT /v1/files/{id}/tags`

**OpenSearch Integration**
- One index per project: `filenest-{project_id}`
- Index mapping: `name`, `mime_type`, `tags`, `metadata`, `ocr_text`, `content_type`, `created_at`, `size`
- `IndexingStage` (updated from Phase 2 stub): indexes full document on `file.ready`

**OCR Stage**
- `OCRStage`: PyMuPDF text layer extraction for PDFs. pytesseract fallback for scanned images.
- Extracted text stored in `ocr_text` table (separate from files for size)
- OCR text indexed into OpenSearch `ocr_text` field

**Search API**
- `POST /v1/projects/{id}/search` — full-text + metadata filters
- Query params: `q` (text), `mime_type`, `tags`, `content_type`, `date_from`, `date_to`, `size_min`, `size_max`
- Response: `hits[]` with file metadata + `highlights` snippets
- `GET /v1/projects/{id}/files` — list with same filters (no full-text)

### Exit Criteria
- Upload a PDF with text → search for a word in it → file appears in results
- Custom metadata schema defined → file uploaded with metadata → metadata searchable
- Files organized in folders correctly

---

## PHASE 4 — Console App

**Duration:** Weeks 10–18 (overlaps with Phases 3 and 5)
**Goal:** Usable web UI. Developers and org admins can manage everything without hitting raw API.

**Docs referenced:** `24_Admin_Dashboard`

### Deliverables

**Auth**
- Fully delegated to IAM via OAuth 2.1 PKCE (wired in Phase 1 skeleton, now connected to real data)
- No `admin_users` table — IAM manages all users and sessions
- Role-based redirect on login: `member` → `/dashboard`, `superadmin` → `/admin`
- Session read via `getServerSession()` in all protected layouts

**Dashboard Pages**

| Page | What it does |
|------|-------------|
| `/login` | Email + password form |
| `/dashboard` | Storage used, API request count, recent files, project list |
| `/projects` | Create project (with domain selection), list all projects |
| `/projects/{id}/files` | File Explorer: browse folders, upload, download, delete, search |
| `/projects/{id}/api-keys` | Create keys (with scope checkboxes), view prefix + last-used, revoke |
| `/projects/{id}/webhooks` | Add/remove webhooks, see delivery history |
| `/projects/{id}/settings` | Name, description, domain (locked after first upload) |
| `/org/team` | Invite members, assign roles (Owner/Admin/Member/Viewer/Billing), remove |
| `/org/usage` | Storage/API/processing meters with progress bars |

**Onboarding Wizard** (shown on first login)
1. Choose domain (Generic / Healthcare / Finance / Legal / Insurance — beta label on non-Generic/Healthcare)
2. Create first project
3. **Storage mode** — two options shown:
   - **Managed** (default, recommended) — FileNest provides and manages the storage. Zero config. File bytes go to FileNest's bucket; metadata stays in FileNest's DB.
   - **Bring Your Own Storage** — customer supplies their own endpoint URL + credentials (MinIO, RestFS, S3, Azure, GCS, R2). Available from Phase 7; shown as "Coming soon" in Phase 4 UI.
4. Generate first API key
5. First file upload (drag-and-drop)

**Project Settings → Storage tab** (`/projects/{id}/settings/storage`)
- Phase 4: shows current storage mode ("Managed — FileNest S3") and a "Switch to custom storage" button (disabled, labeled "Available in Enterprise plan")
- Phase 7: button enabled, opens BYOB configuration form

**SDK Integration in Dashboard**
- File Explorer uses `@filenest/react` `<FileUpload>` component internally
- Upload progress bars, drag-and-drop, file type filtering

### Exit Criteria
- New user signs up → completes onboarding → uploads a file → downloads it from the UI
- Admin can create API keys with specific scopes
- Team member invited via email → accepts → can see the project with correct permissions

---

## PHASE 5 — SDKs & Developer Experience

**Duration:** Weeks 15–20 (overlaps with Phase 4)
**Goal:** External developers can integrate FileNest in under 30 minutes. Clear docs. Working code examples.

**Docs referenced:** `06_SDK_Specification`

### Deliverables

**@filenest/node** (npm)
- `FileNest` client class
- `files.upload(file, options)` — handles single + multipart automatically (>5MB → multipart)
- `files.download(fileId)` — returns stream
- `files.list(projectId, filters)`, `files.get(fileId)`, `files.delete(fileId)`
- `files.search(projectId, query)` — wraps search API
- `webhooks.verify(payload, signature, secret)` — HMAC verification helper
- TypeScript types for all responses

**@filenest/react** (npm)
- `<FileUpload>` — drag-and-drop, progress bars, file type restrictions, size limits
- `<FileList>` — paginated file list with search input
- `<FilePreview>` — renders image/PDF inline (basic, full version in Phase 7)
- Upload token flow: component calls your backend → backend calls FileNest → returns upload token → component uploads directly

**@filenest/nextjs** (npm)
- `createFileNestHandler()` — Next.js API route factory for upload token generation
- Server Actions: `uploadFile()`, `deleteFile()`, `listFiles()`
- `<NextFileUpload>` — wrapper with server action integration

**filenest** (PyPI)
- `FileNestClient` with same surface as Node SDK
- `async_upload()`, `async_download()`, `search()`
- Django and FastAPI integration helpers

**API Documentation**
- OpenAPI 3.1 spec generated from FastAPI routes
- Hosted at `docs.filenest.io` (Mintlify or Stoplight)
- Getting started guide: 5 minutes to first upload
- Code examples in Node, Python, curl for every endpoint
- Webhook integration guide with signature verification

---

## ═══════════════════════════════════
## MVP COMPLETE — End of Phase 5
## ═══════════════════════════════════

At this point FileNest is a working product:
- Developers can upload, process, search, and retrieve files via API or SDK
- Webhooks fire on all file events
- Admin UI is usable for project management
- Virus scanning runs on every upload
- OCR extracts text from PDFs
- Files are searchable

**What is NOT in MVP:**
- Multi-cloud storage (S3 only)
- HIPAA/GDPR/PHI detection
- WORM, legal hold, retention
- Rate limiting enforcement
- Preview generation (Office/video)
- Sharing system
- Bulk operations
- Email notifications
- Full Kubernetes production deployment
- SOAP notes / conversation AI

---

## PHASE 6 — Production Infrastructure

**Duration:** Weeks 20–27
**Goal:** The platform can handle real production traffic. Observable, rate-limited, deployed on Kubernetes.

**Docs referenced:** `14_Kubernetes_Deployment`, `15_Observability`, `16_Rate_Limiting`, `17_Usage_Metering`, `22_Email_Notifications`, `20_Background_Jobs` (upload cleanup + stuck detection)

### Deliverables

**Kubernetes (EKS)**
- 5 node groups: system, api, processing, data, spot
- 4 namespaces: filenest-prod, filenest-data, filenest-monitoring, filenest-security
- Helm chart for all services with values.yaml
- HPA for API and Processing pods (CPU + NATS lag via KEDA)
- External Secrets Operator + AWS Secrets Manager
- `STORAGE_CREDENTIAL_KEY` (32-byte AES-256 master key) stored in AWS Secrets Manager, injected at pod startup via External Secrets Operator — never in env files or logs
- IRSA (IAM Roles for Service Accounts) per service
- NetworkPolicy: default-deny, allowlist per service
- RDS Multi-AZ, Velero daily backup
- `GET /health/ready` wired to HPA readiness probe

**CI/CD**
- GitHub Actions: test → build → push ECR → helm upgrade --atomic
- Alembic migration as Helm pre-install/pre-upgrade Job
- Rollback: `helm rollback` on failed deploy

**Observability**
- OTel SDK auto-instrumentation: FastAPI, SQLAlchemy, Redis, HTTPX
- OTel Collector → Tempo (traces), Prometheus (metrics), Loki (logs)
- structlog JSON logging with request_id + trace_id on every log line
- `AuditLogger`: writes to DB + structlog simultaneously
- 15+ Prometheus metrics (upload count, duration, processing duration, search latency, webhook deliveries, auth failures)
- Grafana dashboards: API Overview, Processing Queue, Storage Usage
- PagerDuty alerts: API down, error rate > 5%, DB connections exhausted, virus scan unavailable
- Slack alerts: P95 latency > 2s, webhook failure rate high
- SLO burn rate alerts (14× for 1h window, 6× for 6h window)

**Rate Limiting**
- Token bucket via Redis Lua atomic script
- Per-org limits (Starter: 100/min, Professional: 1000/min, Enterprise: 10000/min)
- Per-key limits (live: 500/min, test: 200/min, service account: 2000/min)
- Enforces stricter of org vs key
- `X-RateLimit-*` headers on all responses
- 429 response with `retry_after` + `limited_by: "org" | "key"`

**Usage Metering**
- Redis counters per org per month (API calls, upload bytes, download bytes, processing jobs, searches)
- `UsageFlushJob`: Redis → PostgreSQL `usage_snapshots` every 5 minutes
- `StorageCalculationJob`: `SUM(size)` from files table hourly
- `check_upload_allowed()`: enforces storage + processing limits, returns HTTP 402 on breach
- Usage API: `GET /v1/organizations/{id}/usage` with per-metric used/limit/% breakdown

**Email Notifications (Core)**
- AWS SES (primary) + SendGrid (fallback)
- Mandatory notifications only: virus detected, API key revoked, usage at 95%, plan limit reached, legal hold
- Jinja2 templates for mandatory types
- `NotificationWorker`: NATS pull subscriber → render → SES/SendGrid

**Background Jobs (Core)**
- `UploadSessionCleanupJob`: aborts multipart uploads > 24h, marks orphaned file records as FAILED (runs every 30 min)
- `ProcessingStuckDetectionJob`: re-queues processing jobs stuck > 30 min (runs every 5 min)

### Exit Criteria
- 100 concurrent file uploads at once with no errors
- Rate limit headers present on every response
- Prometheus metrics visible in Grafana
- A 30-day S3 lifecycle rule is active for aborting incomplete multipart uploads
- Kubernetes rolling deploy with zero downtime

---

## PHASE 7 — Advanced File Features

**Duration:** Weeks 25–34 (overlaps with Phase 8)
**Goal:** Full feature surface. Sharing, previews, bulk operations, BYOB storage, semantic search.

**Docs referenced:** `12_Storage_Abstraction` (all sections — providers, BYOB, credential schemas §10, encryption §10.3), `07_Security_Architecture` (§7.1 Layer 2), `19_Sharing_System`, `21_Preview_Generation`, `23_Bulk_Operations`, `20_Background_Jobs` (full suite)

### Deliverables

**Storage Abstraction Layer (All Providers)**
- `StorageProvider` Protocol — consistent interface for all backends (`upload`, `download_stream`, `generate_signed_url`, `generate_multipart_upload_id`, `complete_multipart`, `delete`, `health_check`)
- `StorageResolver` — resolves the correct provider per project + environment; branches on `storage_mode` (managed vs. byob)
- Providers implemented:
  - AWS S3 (already in Phase 1 — promoted to protocol-conformant class)
  - Azure Blob Storage
  - Google Cloud Storage
  - MinIO (self-hosted S3-compatible — reuses S3Provider with custom endpoint)
  - Cloudflare R2 (S3-compatible, zero-egress)
  - **RestFS** — REST-based filesystem Docker image; S3-compatible API, customer self-hosts; configured via endpoint URL + access key + secret (reuses S3Provider with custom endpoint)

**BYOB — Dual Storage Mode**
- `storage_mode`: `managed` (FileNest owns the bucket, default) or `byob` (customer supplies their own)
- In both modes: file metadata, audit logs, processing results → FileNest PostgreSQL. Actual file bytes → configured storage target.
- BYOB provider options: S3 (IAM role assumption or static keys), MinIO, RestFS, R2, Azure Blob, GCS
- For S3-compatible BYOB (MinIO, RestFS, R2): customer provides `endpoint_url` + `bucket_name` + `access_key` + `secret_key`
- For AWS S3 BYOB: customer provides IAM role ARN + external ID (FileNest assumes the role via STS)
- Connection verification: `POST /v1/projects/{id}/storage/verify` — FileNest writes + deletes a test object before saving config; returns `{ ok, latencyMs, error }`
- `POST /v1/projects/{id}/storage` — save storage config (triggers verification first)
- `GET /v1/projects/{id}/storage` — returns plaintext fields only (`mode`, `provider`, `endpoint_url`, `bucket_name`, `region`); never returns credentials

**Credential Encryption (`shared/crypto/storage_credentials.py`)**
- All BYOB credentials encrypted with AES-256-GCM before writing to `storage_configs.config_encrypted`
- Per-record key derivation: `HKDF(master_key, info="storage_config:{uuid}")` — a compromised row does not expose other rows' keys
- `STORAGE_CREDENTIAL_KEY` env var (32-byte hex) — loaded at startup, never logged
- Per-provider encrypted JSON schemas (see `12_Storage_Abstraction.md §10.1–10.2` for full table):
  - AWS S3 (IAM role): `{ role_arn, external_id }`
  - AWS S3 (static): `{ access_key_id, secret_access_key }`
  - Azure: `{ account_name, account_key }`
  - GCS: `{ service_account_json }` (full key file)
  - MinIO / RestFS: `{ access_key, secret_key }`
  - R2: `{ account_id, access_key_id, secret_access_key }`
- `StorageConfig.__repr__` masks `config_encrypted` — credentials never appear in logs

**BYOB Console UI (Project Settings → Storage tab)**
- Provider selector: Managed / MinIO / RestFS / AWS S3 / Cloudflare R2 / Azure Blob / Google Cloud
- Dynamic form: fields change per provider (only shows what that provider needs)
- "Test connection" button → calls `POST /v1/projects/{id}/storage/verify` → shows ✓ / ✗ + latency
- Save only enabled after successful verification
- Displays current config in plaintext (endpoint, bucket, region) with "Credentials saved ✓" indicator — never shows raw keys
- Storage migration path: "Switch provider" → verify new endpoint → background migration job (Phase 7)

**Storage Migration Worker**
- `POST /v1/admin/storage/migrate` — triggers background migration from current to new provider
- Dry run returns file count + estimated duration
- Worker: streams each file from source provider → uploads to target → verifies size → updates `storage_key` pointer
- `GET /v1/admin/storage/migrations/{id}` — progress: `{ completed, total, errors, status }`

**Preview Generation**
- `PreviewGenerationStage` added to processing pipeline Phase 3
- PDF → stored as inline preview (PyMuPDF)
- Images → resized to 2048px max, converted to WebP (PIL)
- Office files (DOCX, XLSX, PPTX) → Gotenberg (LibreOffice wrapper) → PDF preview
- OpenDocument formats → Gotenberg
- Video files → ffmpeg poster frame at 5 seconds → WebP
- Audio files → waveform image (soundfile + numpy + PIL)
- `GET /v1/files/{id}/preview` — returns signed preview URL + poster URL + page count
- `<FilePreview>` React component: image lightbox, PDF viewer (PDF.js), Office preview (embedded PDF), video player
- Gotenberg deployed as separate Kubernetes Deployment (2 replicas, 3Gi memory)

**Sharing System**
- `POST /v1/files/{id}/share-links` — create share link (expiry, max downloads, password, allowed email domain)
- 32-byte URL-safe token, public URL: `https://share.filenest.io/s/{token}`
- Password: bcrypt hashed, 10 attempts/hr per token → locked
- Access token: 15-min JWT, single-use (Redis consumed set)
- `GET /s/{token}` — public share page (React, shows preview)
- `POST /s/{token}/access` — verify password → return access token
- `GET /s/{token}/download` — stream file via signed URL proxy
- Healthcare projects: public sharing disabled by default (requires explicit override)

**Bulk Operations**
- All bulk ops are async (202 Accepted with `job_id`)
- `BulkJobWorker`: NATS pull subscriber, FOR UPDATE SKIP LOCKED
- Operations: delete, move, tag, download (zip), metadata update, reprocess
- Per-file compliance check before delete/move
- `skipped` (compliance-blocked) vs `failed` (error) distinction
- Bulk download: streams all files into zip, uploads to storage, returns 1-hour signed URL
- `GET /v1/bulk-jobs/{id}` — job status + per-file results
- SDK: `bulkDelete()`, `bulkMove()`, `bulkTag()`, `bulkDownload()` with `waitForCompletion` option

**Full Background Job Suite**
- `RetentionEnforcementJob`: enforces retention policies (delete/archive/keep) — runs daily
- `AuditLogArchivalJob`: gzip JSONL to S3 Glacier, keeps 90 days hot in PostgreSQL — runs monthly
- `ShareLinkExpiryCleanupJob`: deactivates expired + exhausted share links — runs hourly

**Semantic Search (Embeddings)**
- `EmbeddingStage`: OpenAI `text-embedding-3-small` on extracted text (OCR + metadata)
- OpenSearch `knn_vector` field on index
- `POST /v1/projects/{id}/search` extended: `mode: "semantic" | "full_text" | "hybrid"`
- Hybrid search: BM25 score + cosine similarity, RRF fusion

**Full Email Notifications**
- All 17 notification types from `22_Email_Notifications`
- Notification preferences per user per org
- In-app notifications: `GET /v1/notifications`, `POST /v1/notifications/{id}/read`
- Digest mode: batch notifications into daily summary email

### Exit Criteria
- Upload a DOCX → preview available as PDF in the UI
- Share a file publicly with a password → recipient accesses it without an account
- Bulk delete 500 files in one API call → job completes, status report shows per-file results
- "Find me all files about patient discharge" → semantic search returns relevant results
- Configure a project with a self-hosted MinIO or RestFS endpoint → connection verified → upload a file → it lands in the customer's bucket, not FileNest's
- Credentials visible in DB are opaque (AES-256-GCM ciphertext) — plaintext never appears outside application memory

---

## PHASE 8 — Compliance & Domain Packs

**Duration:** Weeks 30–42 (overlaps with Phase 7)
**Goal:** HIPAA technical safeguards fully implemented. GDPR erasure works. Domain selection system in place.

**Docs referenced:** `07_Security_Architecture` (encryption, KMS), `08_Compliance_Framework`, `09_Healthcare_Pack`, `18_GDPR_Compliance`, `20_Background_Jobs` (GDPR queue + retention)

### Deliverables

**Domain Selection System**
- Domain field on projects: Generic / Healthcare / Finance / Legal / Insurance
- Domain chosen at project creation (onboarding wizard step 1)
- **Immutability lock**: domain locked after first file upload (`validate_profile_change()` blocks with HTTP 422)
- Config dependency validation: `ProjectConfigValidator.validate_with_warnings()` — returns `warnings[]` in API response when configs are partially enabled without their required dependencies
- v1 status: Generic + Healthcare = GA; Finance / Legal / Insurance = Beta (labeled in UI)

**Encryption at Rest (Customer-Managed KMS)**
- AWS KMS CMK per organization (or customer-provided key via BYOK)
- All S3 objects encrypted with per-org KMS key (SSE-KMS)
- KMS key rotation annually (automatic)
- Per-file encryption key reference stored in `files.kms_key_id`
- **Storage credential key rotation**: `STORAGE_CREDENTIAL_KEY` promoted to KMS-backed envelope encryption in Phase 8 — `BackgroundCredentialRekeyJob` decrypts all `storage_configs.config_encrypted` with old key → re-encrypts with new KMS-derived key atomically

**PHI / PII Detection**
- `PHIDetectionStage`: Microsoft Presidio `AnalyzerEngine`, healthcare entity list
- `PIIDetectionStage`: broader entity list (PERSON, EMAIL, PHONE, SSN, CREDIT_CARD, etc.)
- Configurable action per project: `log` | `flag` | `quarantine` | `block`
- Healthcare domain default: `flag` for PHI
- Generic domain: PHI detection off unless manually enabled (generates warning if enabled without audit logs)

**WORM & Legal Hold**
- S3 Object Lock COMPLIANCE mode (7-year default for Healthcare)
- `POST /v1/files/{id}/legal-hold` — places legal hold, logged to audit trail
- `DELETE /v1/files/{id}/legal-hold` — requires explicit admin action, also logged
- Legal hold files: cannot be deleted, moved, or shared publicly
- WORM files: cannot be overwritten or deleted by anyone including FileNest

**Full Audit Logs**
- `audit_logs` table: every file event logged with actor, action, resource, result, IP, user agent
- Tamper-evident: rows are append-only, no UPDATE/DELETE allowed via application
- PHI-touched files: log entries tagged with `phi_involved: true`
- Audit log viewer in admin dashboard: filters by date, action, actor, result; expandable detail panel
- `AuditLogArchivalJob`: exports to gzip JSONL → S3 Glacier, keeps 90 days in hot PostgreSQL

**GDPR Compliance**
- `GDPRErasureRequest` model: PENDING → PROCESSING → COMPLETED / PARTIAL / REJECTED
- `process_erasure_request()`: checks legal hold first, then HIPAA retention
- **GDPR vs HIPAA conflict resolution**: files under HIPAA retention are quarantined (excluded from search/listings/downloads), not deleted. Auto-deleted when `retain_until` passes. HTTP 451 returned for conflicted erasure (GDPR Art. 17(3)(b))
- `erase_file()`: deletes storage object + versions, deletes OCR text, removes from search index, anonymizes file row (status=`erased`), anonymizes audit log metadata (preserves event shape)
- `DataPortabilityExport`: streams all files + metadata.json into zip → signed URL (7-day expiry)
- `GDPRErasureQueueJob`: processes pending requests (FOR UPDATE SKIP LOCKED, max 10 per run)
- DSAR endpoints: `POST /v1/gdpr/erasure-requests`, `GET /v1/gdpr/erasure-requests/{id}`, `POST /v1/gdpr/export`

**Healthcare Domain Pack (GA)**
- FHIR R4 DocumentReference mapping: `POST /v1/healthcare/fhir/document-reference`
- FHIR Binary resource: upload via `POST /v1/healthcare/fhir/binary`
- FHIR Media resource: imaging files
- SMART on FHIR auth flow (EHR-launched app support)
- HIPAA §164.312 technical safeguard coverage (documented in §13 of `09_Healthcare_Pack`)
- XDS.b document registration stub
- BAA signature flow (admin dashboard: org owner must sign before Healthcare domain goes live)

**Config Dependency Warnings (Generic Mode)**
- Enabling PHI detection without HIPAA audit → `warnings[]` in API response with `suggested_fix`
- 3 dependency rules from `08_Compliance_Framework §11.3` enforced

**Full Background Job Suite (Compliance)**
- `RetentionEnforcementJob`: honors WORM, skips legal_hold files, logs every action to audit trail
- `GDPRErasureQueueJob`: processes GDPR queue on 15-minute schedule
- `AuditLogArchivalJob`: monthly Glacier archival

### Exit Criteria
- Upload a file with SSN in it on a Healthcare project → file is flagged with PHI entities in metadata
- Request GDPR erasure on a HIPAA-retained file → file quarantined (HTTP 451), not deleted
- Place a legal hold on a file → attempt to delete it → blocked
- Log into Healthcare project in admin → compliance tab shows HIPAA status checklist

---

## Dependency Graph

```
Phase 1 (Foundation)
  └─→ Phase 2 (Processing & Events)
        ├─→ Phase 3 (Metadata & Search)   ─────────────────────┐
        ├─→ Phase 4 (Admin Dashboard)     ──────────────────── │ ─┐
        └─→ Phase 5 (SDKs)                                     │  │
              │                                                 │  │
              ▼                                                 │  │
         [MVP COMPLETE]  ◄────────────────────────────────── ──┘  │
              │                                                    │
              └─→ Phase 6 (Production Infra)  ◄─────────────────── ┘
                    └─→ Phase 7 (Advanced Features) ─────┐
                                └─→ Phase 8 (Compliance) ◄┘
                                      [v1.0 COMPLETE]
```

Phases 3, 4, 5 run in parallel after Phase 2.
Phases 7 and 8 overlap (start Phase 8 when Phase 7 is 50% done).

---

## What Each Phase Touches

| Service / Component | Introduced | Extended |
|--------------------|-----------|---------|
| PostgreSQL schema | Phase 1 | Every phase |
| S3 / Storage (managed) | Phase 1 | Phase 7 (all providers, BYOB) |
| FastAPI routes | Phase 1 | Every phase |
| NATS JetStream | Phase 2 | Phase 6, 7, 8 |
| Processing pipeline | Phase 2 | Phase 3, 7, 8 |
| Webhooks | Phase 2 | Phase 6 (retry + observability) |
| OpenSearch | Phase 3 | Phase 7 (embeddings) |
| Console App (Next.js) | Phase 4 | Phase 7 (previews, BYOB UI), 8 (compliance) |
| Storage mode UI (managed/BYOB) | Phase 4 (stub, managed only) | Phase 7 (BYOB fully enabled) |
| Node/React SDKs | Phase 5 | Phase 7 (bulk ops) |
| Kubernetes / Helm | Phase 6 | Phase 7 (Gotenberg), 8 |
| Observability | Phase 6 | Phase 8 (audit logs) |
| Rate Limiting | Phase 6 | — |
| Usage Metering | Phase 6 | — |
| Email Notifications | Phase 6 (core) | Phase 7 (full) |
| `STORAGE_CREDENTIAL_KEY` (env) | Phase 6 (Secrets Manager) | Phase 8 (KMS envelope) |
| Preview Generation | Phase 7 | — |
| Sharing System | Phase 7 | — |
| Bulk Operations | Phase 7 | — |
| Storage Abstraction (`StorageResolver` + all providers) | Phase 7 | — |
| BYOB Storage (dual-mode: managed / customer endpoint) | Phase 7 | — |
| RestFS Provider | Phase 7 | — |
| Credential Encryption (`shared/crypto/storage_credentials.py`) | Phase 7 | Phase 8 (KMS rekey) |
| Storage connection verification (`/storage/verify`) | Phase 7 | — |
| Storage Migration Worker | Phase 7 | — |
| PHI / PII Detection | Phase 8 | — |
| WORM / Legal Hold | Phase 8 | — |
| GDPR Erasure | Phase 8 | — |
| FHIR / Healthcare Pack | Phase 8 | — |
| KMS-backed credential rekey job | Phase 8 | — |

---

## Team Assignment Recommendation

| Phase | Backend | Frontend | DevOps | QA |
|-------|---------|----------|--------|-----|
| 1 | 2 | 0 | 1 | 0 |
| 2 | 3 | 0 | 1 | 1 |
| 3 | 2 | 0 | 0 | 1 |
| 4 | 1 (API support) | 2 | 0 | 1 |
| 5 | 1 (API support) | 2 (SDK) | 0 | 1 |
| 6 | 2 | 0 | 2 | 1 |
| 7 | 3 | 1 | 1 | 1 |
| 8 | 3 | 1 | 1 | 2 |

Minimum viable team: **4 engineers** (2 backend, 1 frontend, 1 DevOps/full-stack). MVP in ~26 weeks at this size.
Recommended team: **6–8 engineers**. MVP in ~18 weeks, full platform (v1.0) in ~38 weeks.

---

## Out of Scope for FileNest

The following are AI product features that sit **on top of** FileNest as a separate application. They use FileNest APIs and SDKs as their file backend but are not part of this platform:

- SOAP note generation (LLM-based clinical documentation)
- Audio transcription pipeline (speech-to-text for clinical conversations)
- Conversation memory / multi-turn clinical session management
- AI chat with documents

Those products use FileNest the same way any customer would — via API keys, file uploads, webhooks, and FHIR endpoints.
