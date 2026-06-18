# File Service — Internal Architecture

## Layer diagram

```
HTTP Request
     │
     ▼
┌─────────────────────────────────────────┐
│  router.py  (HTTP layer)                │
│  - Parse request via Pydantic schema    │
│  - Call require_scope()                 │
│  - Delegate to FileService              │
│  - Return typed response schema         │
│  ✗ No SQL, no storage, no business rules│
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  service.py  (Business logic layer)     │
│  - Owns all domain rules                │
│  - Coordinates repo + outbox            │
│  - Commits the DB session               │
│  - Calls StorageResolver (Phase 2)      │
│  ✗ No SQL issued directly               │
└──────┬───────────────────┬──────────────┘
       │                   │
       ▼                   ▼
┌────────────┐    ┌──────────────────────┐
│repository  │    │TransactionalOutbox   │
│.py         │    │Publisher             │
│- All DB    │    │- Enqueues events     │
│  queries   │    │  inside the same     │
│- Tenant    │    │  transaction         │
│  filters   │    └──────────────────────┘
│- flush()   │
│  not       │
│  commit()  │
└──────┬─────┘
       │
       ▼
  PostgreSQL
```

## Dependency direction

```
router → service → repository → database
                → outbox     → database
```

No layer may call a layer above itself. Routes never touch the repository directly.

## Request flow for POST /v1/files/upload

1. FastAPI calls `get_file_service` dependency:
   - `get_db()` opens a session from the primary pool
   - `authenticate_request()` verifies the Bearer token → `TenantContext`
   - `FileService(session, ctx)` is constructed

2. `router.init_upload()` is called:
   - `require_scope("files:upload")` — raises 403 if missing
   - Delegates to `service.init_upload(body)`

3. `service.init_upload()`:
   - Calls `repo.create(...)` → inserts a FileRecord row, calls `flush()` to get the id
   - Generates presigned upload URL (Phase 1: placeholder MinIO URL)
   - Calls `outbox.publish(...)` → inserts an OutboxMessage row (no flush)
   - Calls `session.commit()` → commits both rows atomically
   - Returns `UploadInitResponse`

4. FastAPI serialises the response and sends HTTP 201.

5. Session is released back to the pool by `get_db()`'s `async with` block.

## TenantContext isolation

Every service method reads `organization_id` and `project_id` exclusively from `self._ctx` (the `TenantContext` set by `authenticate_request`). Request body values are never used for tenant filtering. This prevents privilege escalation via manipulated request bodies.

## Error propagation

- Repository raises `NotFoundError`, `ConflictError`, etc. (all `FileNestError` subclasses).
- Service may catch and re-raise with richer context, or let them propagate.
- Router does not catch any `FileNestError` — the global handler in `main.py` converts them.
- FastAPI's built-in 422 handler covers Pydantic validation failures before the route is called.
