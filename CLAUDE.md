# FileNest — CLAUDE.md

FileNest is an **enterprise file infrastructure platform** (think Stripe for files). It sits between client applications and cloud storage providers, providing upload, processing, search, compliance, and webhook delivery as a managed service.

**Current state:** Phase 1 (Foundation) — monorepo scaffold in progress.

---

## Tenant & Data Model

```
User  ──<  Organization  ──<  Project  ──<  File
              (IAM DB)        (FileNest DB)
```

- A **user** can belong to multiple **organizations**.
- An **organization** is the top-level tenant — it maps to a customer account. It owns members, teams, roles, and API keys. Lives in the **IAM database** (BetterAuth `organization` plugin).
- A **project** belongs to one organization and is the unit of storage/processing configuration. Lives in the **FileNest PostgreSQL database** (`backend/app/`). The `organization_id` foreign key links it back to IAM without a cross-DB join.
- **Files, metadata, webhooks, compliance settings** all belong to a project and live in the FileNest database.

### Data ownership rules
| Entity | Database | Why |
|--------|----------|-----|
| Users, sessions, API keys, OAuth clients | IAM (BetterAuth / Prisma) | Auth concern — must stay in the identity layer |
| Organizations, members, teams, roles | IAM (BetterAuth / Prisma) | Tenant identity — Better Auth `organization` plugin owns this |
| Projects | FileNest PostgreSQL | Domain concern — carries storage config, processing config, compliance settings |
| Files, folders, versions | FileNest PostgreSQL | Domain data |
| Webhooks, audit logs, events | FileNest PostgreSQL | Domain data |

### First-login onboarding flow
New users land with `activeOrganizationId = null`. The `(app)` layout detects this and redirects to `/onboarding/create-org?name=<prefill>` where the user confirms (or edits) their org name. After org creation the session is updated and they land on the dashboard.

Steps: **Create org → Get API key → Install SDK → Dashboard**

---

## Skills

Always invoke the relevant skill before starting implementation work:

| Work area | Skill |
|-----------|-------|
| React components, hooks, `@filenest/react`, Next.js client pages | `/filenest-client` |
| FastAPI services, repositories, NATS events, Python SDK, Next.js server components / actions / API routes | `/filenest-server` |

---

## System Map

Three separate deployments — each is its own project:

```
┌─────────────────────────────────────────────────────────────┐
│  iam/  — FileNest IAM                                       │
│  BetterAuth · Prisma · PostgreSQL                           │
│  OAuth 2.1 / OIDC server, user & org management, API keys  │
│  Runs at: IAM_URL (e.g. https://auth.filenest.io)           │
└────────────────────────┬────────────────────────────────────┘
                         │  OAuth 2.1 PKCE
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  frontend/web  — FileNest Console App                       │
│  Next.js · shadcn/ui · @filenest/react                      │
│  Product UI: projects, file explorer, API keys, webhooks    │
│  Runs at: APP_URL (e.g. https://console.filenest.io)        │
└────────────────────────┬────────────────────────────────────┘
                         │  REST API  (Bearer token from IAM)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  backend/  — FileNest FastAPI Backend (single process)      │
│  Python · FastAPI · PostgreSQL · Redis · NATS · OpenSearch  │
│  File operations, processing, search, compliance            │
│  Runs at: API_URL (e.g. https://api.filenest.io)            │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| IAM | BetterAuth v1.5.4, Prisma v7, PostgreSQL (`nextjs-iam`) |
| Console frontend | Next.js 16, React 19, Tailwind CSS v4, shadcn/ui |
| Console auth | OAuth 2.1 PKCE client → IAM |
| Console tables | TanStack Table v8 (shared component system in `modules/client/shared/components/tables/`) |
| Console charts | Recharts |
| Console data | TanStack Query, `@filenest/react`, `@filenest/nextjs` |
| Backend language | Python 3.12, async-first |
| Backend framework | FastAPI + Pydantic v2 |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Database | PostgreSQL 16 (primary + read replica) |
| Cache | Redis 7.x |
| Message broker | NATS JetStream |
| Search | OpenSearch 2.x |
| Object storage | S3 (Phase 1), Azure / GCS / MinIO / R2 / RestFS (Phase 7) |
| Orchestration | Kubernetes + Helm (Phase 6+) |
| Observability | OpenTelemetry, Prometheus, structlog |

---

## Monorepo Structure

```
filenest/
├── iam/                 # BetterAuth IAM — OAuth 2.1 server, API key management
│   └── src/
├── backend/             # Single FastAPI application — all file infrastructure logic
│   ├── app/
│   │   ├── main.py          # FastAPI factory + lifespan
│   │   ├── core/            # config, database, logging, messaging (outbox)
│   │   ├── auth/            # TenantContext, authenticate_request, require_scope
│   │   ├── errors/          # FileNestError hierarchy + exception handlers
│   │   ├── models/          # SQLAlchemy ORM: Project, File
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── repositories/    # DB access layer (tenant-scoped queries)
│   │   ├── services/        # Business logic layer
│   │   ├── storage/         # StorageProvider protocol + S3 impl + StorageResolver
│   │   └── routers/         # HTTP handlers (thin — delegate to services)
│   ├── migrations/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── alembic/versions/
│   ├── scripts/
│   │   └── seed_dev.py      # Bootstrap dev DB (project only — keys via IAM)
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   └── web/             # FileNest Console — Next.js OAuth client of the IAM
│       └── src/
│           ├── app/
│           │   ├── [locale]/
│           │   │   ├── (auth)/              # OAuth 2.1 PKCE flow
│           │   │   │   ├── login/           # Generates PKCE state+verifier, redirects to IAM
│           │   │   │   ├── callback/        # Receives code+state, calls /api/auth/token
│           │   │   │   ├── signup/          # Redirects to IAM signup page
│           │   │   │   ├── forgot-password/ # Redirects to IAM forgot-password
│           │   │   │   ├── reset-password/
│           │   │   │   └── verify-email/
│           │   │   ├── (onboarding)/        # First-login wizard (no active org required)
│           │   │   │   └── onboarding/
│           │   │   │       ├── create-org/  # Name + slug; pre-filled from user.name
│           │   │   │       ├── get-api-key/ # Generate fn_ key; shown once
│           │   │   │       └── install-sdk/ # Node.js / Python snippets → /dashboard
│           │   │   ├── (app)/               # Authenticated product routes (requires active org)
│           │   │   │   ├── dashboard/       # Usage summary, recent files, quick actions
│           │   │   │   ├── projects/        # List projects in active org
│           │   │   │   │   └── [projectId]/
│           │   │   │   │       ├── files/       # File explorer (<FileExplorer>)
│           │   │   │   │       ├── api-keys/    # Project-scoped API key management
│           │   │   │   │       ├── webhooks/    # Webhook endpoint config
│           │   │   │   │       └── settings/    # Project config (storage, compliance)
│           │   │   │   └── org/
│           │   │   │       ├── team/            # Invite members, assign roles
│           │   │   │       └── usage/           # Storage / API / processing meters
│           │   │   └── (admin)/             # Superadmin-only (Phase 4+)
│           │   │       ├── users/
│           │   │       ├── organizations/
│           │   │       └── projects/
│           │   ├── api/
│           │   │   ├── auth/token/          # Server-side OAuth token exchange with IAM
│           │   │   ├── onboarding/org/      # Creates org in IAM + activates it
│           │   │   ├── filenest-token/      # Upload token endpoint for @filenest/react
│           │   │   └── webhooks/filenest/   # FileNest event webhook receiver
│           │   └── layout.tsx              # Root layout with <FileNestProvider>
│           ├── modules/
│           │   ├── client/                  # React components + hooks per feature
│           │   │   ├── auth/
│           │   │   ├── projects/
│           │   │   ├── files/
│           │   │   └── shared/              # Navbar, sidebar, error boundaries
│           │   └── server/
│           │       ├── auth/                # getServerSession(), session types
│           │       ├── actions/             # zsa server actions per feature
│           │       └── utils/
│           ├── components/ui/               # shadcn/ui components
│           └── lib/
├── sdks/
│   ├── @filenest/core   # Shared HTTP client + types
│   ├── @filenest/node   # Node.js SDK
│   ├── @filenest/react  # React components + hooks
│   ├── @filenest/nextjs # Next.js server utilities
│   └── filenest/        # Python SDK (PyPI)
├── migrations/alembic/
├── tests/
├── docker/
├── helm/
└── scripts/
```

---

## Console App — Auth (OAuth 2.1 PKCE)

The console app is a **pure OAuth 2.1 client** — it has no BetterAuth instance of its own. Authentication is fully delegated to the IAM (`nextjs-iam`). The pattern is identical to `E:\work\code\drgodly`.

### Flow

```
1. User hits /login
   → generate random state (CSRF) + code_verifier (PKCE)
   → store both in localStorage
   → redirect to: IAM_URL/api/auth/oauth2/authorize?client_id=...&code_challenge=...

2. User authenticates on the IAM (login/signup/2FA all handled there)
   → IAM redirects back to: APP_URL/callback?code=...&state=...

3. /callback page (client component)
   → validate state matches localStorage value
   → POST /api/auth/token { code, code_verifier, redirect_uri }

4. /api/auth/token (server route)
   → forward to IAM_URL/api/auth/oauth2/token with client_secret
   → receive JWT access token + refresh token
   → set httpOnly session cookie
   → return { redirectUrl } for role-based navigation

5. Browser redirects to redirectUrl (e.g. /dashboard)
```

### Key files

| File | Purpose |
|------|---------|
| `app/[locale]/(auth)/login/page.tsx` | PKCE init — generates state/verifier, redirects to IAM |
| `app/[locale]/(auth)/callback/page.tsx` | PKCE callback — validates state, calls token exchange |
| `app/api/auth/token/route.ts` | Server-side token exchange with IAM (holds client secret) |
| `modules/server/auth/get-session.ts` | `getServerSession()` — reads JWT from cookie for server components |

### Environment variables (console app)

```env
NEXT_PUBLIC_BETTER_AUTH_URL=https://auth.filenest.io   # IAM URL
NEXT_PUBLIC_BETTER_AUTH_CLIENT_ID=...                   # OAuth client ID (registered in IAM)
BETTER_AUTH_CLIENT_SECRET=...                           # OAuth client secret (server-only)
NEXT_PUBLIC_APP_URL=https://console.filenest.io         # This app's URL (for redirect_uri)
FILENEST_API_KEY=fn_live_...                            # For server-side FileNest SDK calls
NEXT_PUBLIC_FILENEST_PROJECT_ID=...                     # For browser-side @filenest/react
```

### IAM configuration (already applied)

The IAM at `iam/` is already configured for FileNest:

| Setting | Value |
|---------|-------|
| `apiKey({ defaultPrefix })` | `"fn_"` |
| `agentAuth.providerName` | `"FileNest IAM"` |
| Session hook | New users → `activeOrganizationId: null` → triggers onboarding wizard |
| Email template footer | `"FileNest"` |
| Seed org | `slug: "filenest"` (created by `pnpm seed:admin`) |

A new OAuth client record must be created in the IAM for the console app (superadmin → OAuth Clients → Create). Register `NEXT_PUBLIC_APP_URL/callback` as the redirect URI.

---

## Console App — Modules Folder Structure

The `frontend/web/src/modules/` directory is split into three layers. Never mix concerns across layers.

```
modules/
├── client/                        # React components and hooks (browser)
│   ├── (marketing)/               # Landing page, feature pages, RootNavbar, Footer
│   │   ├── components/            # Section components: Hero, Features, SdkSection, …
│   │   └── pages/                 # Full-page components: CompliancePage, SearchPage, …
│   ├── auth/                      # Login/callback/signup UI components
│   ├── dashboard/                 # Dashboard client components + hooks
│   ├── projects/                  # Projects list + project detail client components
│   ├── files/                     # File explorer, upload, preview client components
│   ├── onboarding/                # Onboarding wizard step components
│   └── shared/                    # Cross-feature client UI
│       └── components/
│           ├── layout/            # AppSidebar, Header, OrgSwitcher, ThemeSwitcher
│           └── tables/            # TanStack Table shared column helpers
├── entities/                      # Framework-free types and Zod schemas (no imports from client/server)
│   └── schemas/                   # Zod schemas — one file per domain entity
├── server/                        # Server-only code (Next.js server components, actions, utils)
│   ├── auth/                      # getServerSession(), session types
│   ├── actions/                   # zsa server actions per feature (one file per feature)
│   └── utils/                     # Shared server utilities
```

### Key rules

- **`client/` is browser code** — all files that use hooks, state, or browser APIs live here. Mark with `'use client'` when needed.
- **`server/` is server-only code** — never import server modules in client components. Server actions go in `server/actions/`.
- **`entities/schemas/` has no React/Next.js imports** — pure Zod + TypeScript. Both client and server can import from here.
- **Split large files** — if a component grows beyond ~120 lines of JSX, split sub-sections into focused components in the same folder.
- **`(marketing)/` in client mirrors the route group** — keeps marketing and app code cleanly separated inside `modules/client/`.
- **One file per domain entity** in `entities/schemas/` (e.g. `file.ts`, `project.ts`, `organization.ts`).
- **Reference app:** the drgodly application (`E:\work\code\drgodly`) for folder structure and theme system.

---

## Console App — Clean Architecture Rules

### Route protection
- `(auth)/` routes — public, no session required.
- `(onboarding)/` routes — session required, but `activeOrganizationId` may be null. Redirects to `/dashboard` if org already set (idempotent).
- `(app)/` routes — session + `activeOrganizationId` required. Layout redirects to `/login` if no session, to `/onboarding/create-org` if no active org.
- `(admin)/` routes — layout additionally checks that `session.user.role === "superadmin"`.

### Server components / server actions
- Fetch initial data via `filenestServer()` from `@filenest/nextjs/server` — not client-side on page load.
- All mutations go through **zsa server actions** in `modules/server/actions/`.
- Call `revalidatePath()` after mutations.
- `api/filenest-token/route.ts` must call `getServerSession()` before issuing a token — never issue tokens to unauthenticated requests.
- `api/webhooks/filenest/route.ts` must verify `x-filenest-signature` before processing.

### Client components
- Use `@filenest/react` components for all file UI (`<FileUpload>`, `<FileExplorer>`, `<FilePreview>`, `<FileViewer>`).
- The browser never holds the FileNest API key. `<FileNestProvider tokenEndpoint="/api/filenest-token">` handles token exchange.
- `NEXT_PUBLIC_FILENEST_PROJECT_ID` is the only FileNest env var safe for the browser.

---

## FastAPI — Clean Architecture Rules

Single FastAPI application in `backend/`. Dependency direction is strict: **routers → services → repositories → DB**. No layer skips another.

```
backend/app/
├── main.py              # FastAPI app factory + lifespan
├── core/                # Shared infrastructure (config, db, logging, messaging)
├── auth/                # Authentication (TenantContext, dependencies, JWKS + API key verify)
├── errors/              # Domain exception hierarchy + FastAPI exception handlers
├── models/              # SQLAlchemy ORM models (Project, File, ...)
├── schemas/             # Pydantic request/response DTOs (never return ORM objects)
├── repositories/        # All DB queries — tenant-scoped, no business logic
├── services/            # All business logic — coordinates repo + storage + outbox
├── storage/             # StorageProvider protocol, S3 impl, StorageResolver singleton
└── routers/             # HTTP handlers — validate input, call service, return schema
```

### Mandatory patterns

- **Routes are thin.** Validate via Pydantic schemas, call one service method, return a response model. No SQL, no storage calls.
- **Service owns all business logic.** Load config, validate policies, coordinate repo + storage + events.
- **Repository owns all DB access.** Every query must include `organization_id` + `project_id` filters. Use `db.flush()` (not `db.commit()`) to get DB-assigned IDs — the session context manager commits.
- **Transactional outbox for all events.** Write to the `events` table in the same transaction as the business operation. The `OutboxWorker` publishes to NATS separately. Never call NATS directly from a service method.
- **Audit every mutation.** Upload, delete, download, legal-hold, WORM, metadata-update must all call `AuditLogger.log()` inside the same DB transaction.
- **Storage provider is always injected.** Never import a specific provider class (`S3Provider`, etc.) in service code. Always resolve via `StorageResolver.get_provider(project_id, environment)`. The resolver handles both `managed` mode (FileNest platform bucket) and `byob` mode (customer-supplied endpoint).
- **Config from `ProjectConfig`.** Industry-specific behaviour (HIPAA, WORM, retention) comes from the project's stored configuration, never from hardcoded conditionals.
- **Always include tenant context in log entries.** Every `logger.info/error` call must include `organization_id` and `project_id`.

### Auth (FastAPI backend)

Token prefixes validated by the backend:
- `fn_live_...` / `fn_test_...` → API key (server-to-server, generated by FileNest backend)
- `fn_sa_...` → Service account
- `fn_upload_token_...` → Short-lived browser upload token

Use `Depends(require_scope("scope:name"))` on every route. Available scopes:
`files:upload`, `files:download`, `files:read`, `files:delete`, `files:update_metadata`,
`api_keys:create`, `api_keys:revoke`, `projects:read`, `projects:update`,
`audit:read`, `compliance:manage`

### Exceptions — raise these, never return raw HTTP errors

```
FileNotFoundError         → 404
AuthenticationError       → 401
AuthorizationError        → 403
MetadataValidationError   → 422
WORMViolationError        → 409
LegalHoldViolationError   → 409
FileTooLargeError         → 413
FileQuarantinedError      → 409
```

All in `shared/exceptions/`. The global handler converts them to the standard JSON error envelope.

---

## Documentation Standards

Every Python file and every TypeScript/TSX file must be documented at two levels. Apply this rule to all new files and when touching existing ones.

### File-level docstring — Python

Every `.py` file opens with a module docstring as its **first statement** (before imports):

```python
"""
<package.module> — <one-line summary of the file's responsibility>

<2–4 sentences: what this module does, who uses it, and any important constraint
or invariant a new reader needs to know before reading the code.>

Usage:
    from shared.auth import authenticate_request, require_scope
"""
```

### File-level comment — TypeScript / TSX

Every `.ts` / `.tsx` file opens with a JSDoc block:

```ts
/**
 * <ComponentOrModule> — <one-line summary>
 *
 * <2–4 sentences of context.>
 *
 * @module
 */
```

### Code-level documentation

- Every public **class** must have a class docstring explaining its single responsibility and any lifecycle notes (e.g., "must be constructed inside a DB session context").
- Every public **method / function** must have a docstring with: what it does, non-obvious parameters, return value, and which checked exceptions it raises.
- Inline `#` comments for any non-obvious logic, workaround, or invariant — one short line, not a paragraph.
- Do **not** restate what the code already says. The docstring explains the *why* and the *contract*; the code explains the *how*.

### Module `docs/` folder

Every Python package (each service and the `shared/` package) must contain a `docs/` directory with Markdown files:

| Package | Required docs files |
|---------|-------------------|
| `shared/` | `overview.md`, `auth.md`, `config.md`, `database.md`, `cache.md`, `messaging.md`, `exceptions.md`, `logging.md` |
| `services/file/` | `overview.md`, `api.md`, `architecture.md`, `upload-flow.md` |
| `services/identity/` | `overview.md`, `api.md`, `architecture.md` |
| `services/project/` | `overview.md`, `api.md`, `architecture.md` |
| Each new service | `overview.md`, `api.md`, `architecture.md` + flow docs as needed |

Each docs file must include these sections where applicable:
- **Purpose** — what the module/component does, in one paragraph
- **Usage** — import paths and a working code example
- **Key types / classes / functions** — brief description of main exports
- **Patterns & rules** — constraints a developer must follow when extending this module

Auto-generated API references (OpenAPI schema, type definitions) are **not** duplicated in `docs/` — those live at `/docs` on the running service.

---

## Architecture Principles

1. **Stateless services** — state lives in PostgreSQL, Redis, or object storage. Never in service memory.
2. **Async by default** — upload returns immediately after persisting the file record. Processing happens in background via NATS.
3. **Fail-safe processing** — pipeline failures do not block file availability. Files are downloadable before processing completes.
4. **Event-driven** — every significant state change emits a NATS event. Subject format: `filenest.{org_id}.{project_id}.{event_type}`.
5. **Configuration-driven** — no hardcoded industry logic. Behaviour comes from `ProjectConfig` resolved from the database.
6. **Multi-tenancy by construction** — `organization_id` + `project_id` in every query, every log line, every NATS event payload.

---

## Implementation Phases (current: pre-Phase 1)

| Phase | Goal | Status |
|-------|------|--------|
| 1 — Foundation | Auth, single-file upload to S3, basic file CRUD | Not started |
| 2 — Processing & Events | Virus scan, MIME validation, NATS, webhooks, multipart upload | Not started |
| 3 — Metadata & Search | Custom schemas, folders, tags, OCR, OpenSearch | Not started |
| 4 — Console App | Next.js OAuth client, file explorer, API key management | Not started |
| 5 — SDKs | `@filenest/node`, `@filenest/react`, `@filenest/nextjs`, `filenest` PyPI | Not started |
| 6 — Production | Kubernetes, observability, rate limiting, usage metering | Not started |
| 7 — Advanced Features | All storage providers, previews, sharing, bulk ops, semantic search | Not started |
| 8 — Compliance | HIPAA, GDPR, WORM, legal hold, PHI detection, FHIR | Not started |

**MVP = Phases 1–5.** Do not build Phase 6+ features ahead of their phase.

---

## Dev Environment

Local stack runs via `docker compose up`:
- PostgreSQL 16
- Redis 7
- MinIO (local S3-compatible)
- NATS JetStream
- ClamAV

`just dev` starts everything in one command (Phase 1 deliverable).

The IAM (`nextjs-iam`) runs separately on its own port. Console app points `NEXT_PUBLIC_BETTER_AUTH_URL` at it.

---

## Key Files (once implemented)

**FastAPI backend:**

| File | Purpose |
|------|---------|
| `shared/config/settings.py` | Single `Settings` object (Pydantic BaseSettings) |
| `shared/database/session.py` | `get_db`, `get_read_db`, session context manager |
| `shared/auth/middleware.py` | `authenticate_request` — token → `AuthContext` |
| `shared/auth/permissions.py` | `require_scope(scope)` dependency |
| `shared/messaging/outbox.py` | `TransactionalOutboxPublisher`, `OutboxWorker` |
| `shared/exceptions/__init__.py` | Full exception hierarchy |
| `services/storage/resolver.py` | `StorageResolver.get_provider(project_id, env)` |
| `services/storage/provider.py` | `StorageProvider` Protocol |
| `services/processing/pipeline.py` | `PipelineExecutor` — stage registry + orchestration |

**Console app:**

| File | Purpose |
|------|---------|
| `frontend/web/src/app/[locale]/(auth)/login/page.tsx` | PKCE init — redirect to IAM |
| `frontend/web/src/app/[locale]/(auth)/callback/page.tsx` | PKCE callback + state validation |
| `frontend/web/src/app/api/auth/token/route.ts` | Server-side token exchange with IAM |
| `frontend/web/src/modules/server/auth/get-session.ts` | `getServerSession()` for server components |
| `frontend/web/src/app/[locale]/(onboarding)/layout.tsx` | Onboarding shell — redirects to dashboard if org already set |
| `frontend/web/src/app/[locale]/(onboarding)/onboarding/create-org/page.tsx` | Step 1 — org name + slug, pre-filled from user.name |
| `frontend/web/src/app/api/onboarding/org/route.ts` | Creates org in IAM + activates it |
| `frontend/web/src/app/api/filenest-token/route.ts` | Upload token for `@filenest/react` |
| `frontend/web/src/app/api/webhooks/filenest/route.ts` | Webhook receiver |
| `frontend/web/src/app/layout.tsx` | Root layout with `<FileNestProvider>` |

---

## Planning Documents

All 24 engineering specs are in `dev-docs/plan/`. Read the relevant doc before implementing any feature:

| Doc | Covers |
|-----|--------|
| `00_Implementation_Roadmap.md` | Phase-by-phase build order — **read first** |
| `02_System_Architecture.md` | Service map, communication patterns, data flows |
| `03_Database_Design.md` | Full schema — tables, columns, indexes |
| `04_Backend_Architecture.md` | FastAPI service internals, all service implementations |
| `05_API_Specification.md` | REST endpoints, request/response shapes |
| `06_SDK_Specification.md` | Node, React, Next.js, Python SDK APIs |
| `07_Security_Architecture.md` | Auth, encryption, API key design |
| `08_Compliance_Framework.md` | WORM, legal hold, retention, config deps |
| `09_Healthcare_Pack.md` | FHIR, HIPAA, PHI detection |
| `10_Search_Architecture.md` | OpenSearch mappings, query builder |
| `11_Event_Architecture.md` | NATS streams, subjects, consumer config |
| `12_Storage_Abstraction.md` | Provider protocol, BYOB, resolver |
| `13_Processing_Pipelines.md` | Stage registry, virus scan, OCR, PHI, previews |
| `24_Admin_Dashboard.md` | Dashboard pages, onboarding wizard |
