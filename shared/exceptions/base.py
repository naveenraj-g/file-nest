"""
shared.exceptions.base — FileNest exception hierarchy.

All exceptions raised inside service, repository, and middleware code must
subclass FileNestError. The global exception handler registered in each
service's main.py converts these into the standard JSON error envelope
so no service code ever needs to construct HTTPException directly.

Standard error envelope returned to API clients:
    {"error": "<CODE>", "message": "<human text>", "detail": {...}}

Usage:
    from shared.exceptions import NotFoundError, ValidationError

    raise NotFoundError("File abc123 not found")
    raise ValidationError("content_type is required", detail={"field": "content_type"})
"""
from http import HTTPStatus


class FileNestError(Exception):
    """
    Base class for all FileNest domain errors.

    Subclasses set `status_code` (HTTP) and `code` (machine-readable string)
    at the class level. The global handler reads both when building the
    JSON error envelope.

    Args:
        message: Human-readable description shown to API clients.
        detail: Optional structured data for programmatic error handling.
    """

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFoundError(FileNestError):
    """Raised when a requested resource does not exist or is outside the caller's tenant scope."""

    status_code = HTTPStatus.NOT_FOUND
    code = "NOT_FOUND"


class PermissionDeniedError(FileNestError):
    """Raised when the caller's token lacks a required scope or crosses a tenant boundary."""

    status_code = HTTPStatus.FORBIDDEN
    code = "PERMISSION_DENIED"


class ValidationError(FileNestError):
    """Raised when business-rule validation fails (beyond what Pydantic schema validation catches)."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "VALIDATION_ERROR"


class ConflictError(FileNestError):
    """
    Raised when an operation is rejected due to current resource state.

    Examples: WORM policy prevents overwrite, legal hold prevents deletion,
    duplicate key on create.
    """

    status_code = HTTPStatus.CONFLICT
    code = "CONFLICT"


class StorageError(FileNestError):
    """Raised when the underlying storage provider returns an unexpected error."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = "STORAGE_ERROR"


class QuotaExceededError(FileNestError):
    """Raised when a project's storage or API-call quota would be exceeded."""

    status_code = HTTPStatus.TOO_MANY_REQUESTS
    code = "QUOTA_EXCEEDED"


class VirusScanError(FileNestError):
    """Raised when ClamAV detects a threat in an uploaded file."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "VIRUS_DETECTED"


class ProcessingError(FileNestError):
    """Raised when a processing pipeline stage fails in a non-retryable way."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    code = "PROCESSING_ERROR"


class OutboxError(FileNestError):
    """Raised when writing to the transactional outbox table fails."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    code = "OUTBOX_ERROR"
