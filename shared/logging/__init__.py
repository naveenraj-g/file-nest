"""
shared.logging — Structured logging setup via structlog.

Call `configure_logging()` once in each service's lifespan startup handler.
After that, obtain a bound logger anywhere with `get_logger(__name__)`.

In development the logger emits coloured console output. In production it emits
newline-delimited JSON, suitable for log aggregators (Datadog, Loki, etc.).

Tenant context variables (organization_id, project_id) are merged automatically
from structlog's contextvars — set them via `structlog.contextvars.bind_contextvars`
at the start of each request.

Usage:
    from shared.logging import configure_logging, get_logger

    configure_logging()               # once, in lifespan
    log = get_logger(__name__)
    log.info("file.uploaded", file_id=file_id, org_id=org_id)
"""
import logging

import structlog

from shared.config import settings


def configure_logging() -> None:
    """
    Configure structlog with processors appropriate for the current environment.

    Must be called exactly once before any log statement is emitted, typically
    inside the FastAPI lifespan startup handler.
    """
    log_level = logging.DEBUG if settings.is_dev else logging.INFO

    structlog.configure(
        processors=[
            # Merge contextvars (e.g. request-scoped org/project ids) into every log event
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            # Human-readable in dev; JSON in production
            structlog.dev.ConsoleRenderer()
            if settings.is_dev
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Return a structlog BoundLogger for the given module name.

    Args:
        name: Typically `__name__` of the calling module.

    Returns:
        A structlog BoundLogger. All log events include the module name
        and any contextvars already bound for the current async task.
    """
    return structlog.get_logger(name)
