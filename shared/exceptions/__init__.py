"""
shared.exceptions — Public API for the FileNest exception hierarchy.

Import all domain exceptions from here. The global handler in each service's
main.py converts every FileNestError subclass into the standard JSON envelope
automatically — never raise HTTPException directly in service or repository code.

Usage:
    from shared.exceptions import NotFoundError, ConflictError

    raise NotFoundError("File not found")
"""
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
