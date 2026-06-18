# shared.exceptions — Error Hierarchy

## Purpose

Defines the `FileNestError` base class and all domain-specific subclasses. Every service registers a global exception handler that converts any `FileNestError` into the standard JSON error envelope. Service and repository code must raise these exceptions — never construct `HTTPException` directly.

## Standard error envelope

```json
{
  "error": "NOT_FOUND",
  "message": "File abc123 not found",
  "detail": {}
}
```

`error` is the machine-readable code; `message` is human-readable; `detail` is optional structured data for programmatic error handling.

## Exception map

| Exception class | HTTP status | `error` code | When to raise |
|----------------|-------------|-------------|---------------|
| `FileNestError` | 500 | `INTERNAL_ERROR` | Base class — do not raise directly |
| `NotFoundError` | 404 | `NOT_FOUND` | Resource missing or outside caller's tenant scope |
| `PermissionDeniedError` | 403 | `PERMISSION_DENIED` | Missing scope or cross-tenant access attempt |
| `ValidationError` | 422 | `VALIDATION_ERROR` | Business-rule failure beyond Pydantic schema validation |
| `ConflictError` | 409 | `CONFLICT` | WORM violation, legal hold, duplicate key |
| `StorageError` | 502 | `STORAGE_ERROR` | Unexpected error from S3/MinIO/Azure |
| `QuotaExceededError` | 429 | `QUOTA_EXCEEDED` | Storage or API call quota would be exceeded |
| `VirusScanError` | 422 | `VIRUS_DETECTED` | ClamAV found a threat in an uploaded file |
| `ProcessingError` | 500 | `PROCESSING_ERROR` | Non-retryable pipeline stage failure |
| `OutboxError` | 500 | `OUTBOX_ERROR` | Failed to write to the transactional outbox table |

## Usage

```python
from shared.exceptions import NotFoundError, ConflictError, ValidationError

# Simple raise
raise NotFoundError("File abc123 not found")

# With structured detail
raise ValidationError(
    "content_type is not allowed for this project",
    detail={"content_type": "application/x-msdownload", "allowed": ["image/*", "application/pdf"]}
)
```

## Registering the global handler (in each service's main.py)

```python
from shared.exceptions import FileNestError
from fastapi.responses import JSONResponse

@app.exception_handler(FileNestError)
async def filenest_error_handler(request, exc: FileNestError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message, "detail": exc.detail},
    )
```

## Patterns & rules

- Raise the most specific subclass available — never raise the bare `FileNestError`.
- Do not catch-and-re-raise `FileNestError` inside service code just to log it — the global handler logs it at the boundary.
- Pydantic schema validation errors (wrong types, missing fields) are handled by FastAPI's built-in 422 handler — you do not need `ValidationError` for those.
