# shared.messaging — Transactional Outbox

## Purpose

Guarantees reliable event delivery to NATS JetStream using the **transactional outbox pattern**. This prevents the "dual-write problem" where a service could commit a DB change but crash before publishing the NATS message (or vice versa).

## How it works

```
┌──────────────────────────────────────────┐
│  Service (within a single DB transaction) │
│                                           │
│  1. INSERT file record                    │
│  2. INSERT outbox_messages row            │
│  3. COMMIT  ← both rows committed atomically │
└─────────────────────┬────────────────────┘
                      │
              (separate process)
                      ▼
┌──────────────────────────────────────────┐
│  OutboxWorker (Phase 2)                  │
│                                           │
│  4. SELECT unpublished rows              │
│  5. Publish each to NATS JetStream       │
│  6. UPDATE published_at = now()          │
└──────────────────────────────────────────┘
```

## Usage

```python
from shared.messaging import TransactionalOutboxPublisher

# Inside a service method, BEFORE committing the session:
publisher = TransactionalOutboxPublisher(session)
await publisher.publish(
    subject=f"filenest.{ctx.organization_id}.{ctx.project_id}.file.uploaded",
    payload={"file_id": "abc", "size_bytes": 1024},
    organization_id=ctx.organization_id,
    project_id=ctx.project_id,
)

# Then commit — both the business row and outbox row are committed atomically
await session.commit()
```

## NATS subject format

```
filenest.<organization_id>.<project_id>.<event_type>
```

Examples:
- `filenest.org_123.proj_456.file.upload.initiated`
- `filenest.org_123.proj_456.file.processing.completed`
- `filenest.org_123.proj_456.file.deleted`

## outbox_messages table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `subject` | varchar | NATS subject |
| `payload` | text | JSON-serialised event body |
| `organization_id` | varchar | For filtering / monitoring |
| `project_id` | varchar | For filtering / monitoring |
| `created_at` | timestamptz | When the event was enqueued |
| `published_at` | timestamptz | Set by OutboxWorker after delivery; `NULL` = pending |

## Patterns & rules

- **Never** publish to NATS directly from service code — always use `TransactionalOutboxPublisher`.
- The publisher must be used **inside** the same transaction as the business operation.
- The publisher does NOT flush or commit — the service layer owns the transaction boundary.
- Do not read from the outbox table in service code — that is the OutboxWorker's job.
