# shared.logging — Structured Logging

## Purpose

Configures structlog for the entire backend. In development, logs are emitted as human-readable coloured console output. In production, they are newline-delimited JSON suitable for Datadog, Loki, or any log aggregator.

## Setup (once per service)

Call `configure_logging()` as the first thing in your service's lifespan startup:

```python
from shared.logging import configure_logging

@asynccontextmanager
async def lifespan(app):
    configure_logging()
    yield
```

## Getting a logger

```python
from shared.logging import get_logger

log = get_logger(__name__)

log.info("file.uploaded", file_id="abc", size_bytes=1024)
log.warning("quota.approaching", org_id="org123", usage_pct=0.9)
log.error("storage.error", exc_info=True, provider="s3", bucket="filenest")
```

## Binding request-scoped context

Use structlog's contextvars to bind tenant IDs once per request so they appear on every subsequent log entry automatically:

```python
import structlog

structlog.contextvars.bind_contextvars(
    organization_id=ctx.organization_id,
    project_id=ctx.project_id,
    request_id=request.headers.get("X-Request-Id"),
)
```

Clear them at the end of the request (or let FastAPI's middleware handle it):

```python
structlog.contextvars.clear_contextvars()
```

## Log event naming convention

Use dot-separated, lowercase strings that describe `<domain>.<action>`:

```
file.upload.initiated
file.processing.started
file.processing.completed
file.deleted
quota.exceeded
storage.presign.failed
```

## Mandatory fields in every log entry

Per the CLAUDE.md architecture rules, every log call in service/repository code must include:

| Field | Source |
|-------|--------|
| `organization_id` | `ctx.organization_id` |
| `project_id` | `ctx.project_id` |

These are typically bound via contextvars at request start so you don't need to pass them manually every time.

## Log levels

| Level | When to use |
|-------|------------|
| `DEBUG` | Per-query SQL, detailed processing steps (dev only) |
| `INFO` | Normal lifecycle events (upload initiated, file ready) |
| `WARNING` | Recoverable problems (retry, quota approaching) |
| `ERROR` | Unexpected failures that need attention |
