"""app.errors — Domain exceptions and FastAPI error handlers."""
from .base import (
    ConflictError,
    FileNestError,
    NotFoundError,
    OutboxError,
    PermissionDeniedError,
    ProcessingError,
    QuotaExceededError,
    StorageError,
    ValidationError,
    VirusScanError,
)

__all__ = [
    "FileNestError",
    "NotFoundError",
    "PermissionDeniedError",
    "ValidationError",
    "ConflictError",
    "StorageError",
    "QuotaExceededError",
    "VirusScanError",
    "ProcessingError",
    "OutboxError",
]
