"""
app.main — FileNest FastAPI application factory.

Single-process FastAPI backend handling file operations, project management,
and storage abstraction. Authentication is delegated entirely to the IAM
(BetterAuth) — this service only verifies tokens, never issues them.

Run locally:
    uv run uvicorn app.main:app --reload --port 8000

API docs: http://localhost:8000/docs
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from app.core import nats as nats_core
from app.core.config import settings
from app.core.cors_middleware import PerProjectCORSMiddleware
from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging, get_logger
from app.core.messaging import OutboxWorker
from app.di.container import Container
from app.workers.processing import ProcessingWorker
from app.workers.webhook import WebhookWorker
from app.errors.base import FileNestError
from app.errors.handlers import (
    filenest_error_handler,
    http_exception_handler,
    integrity_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.routers import api_router
from app.routers.health import router as health_router
from app.storage.resolver import storage_resolver

# Import all models so Alembic can discover the full schema in one pass
import app.models  # noqa: F401
import app.core.messaging  # noqa: F401

configure_logging()
logger = get_logger(__name__)

container = Container()


async def _apply_startup_cors() -> None:
    """
    Ensure the platform-managed default bucket exists and has CORS applied.

    Runs every time the backend starts. create_bucket() is idempotent — safe
    to call even if the bucket already exists.
    """
    _default_buckets = {
        "s3": settings.s3_bucket_name,
        "minio": settings.minio_bucket_name,
        "rustfs": settings.rustfs_bucket_name,
        "r2": settings.r2_bucket_name,
    }
    p = settings.default_storage_provider.lower()
    bucket = _default_buckets.get(p, "filenest")
    try:
        provider = await storage_resolver.get_provider("_startup")
        await provider.create_bucket(bucket)
        await provider.set_bucket_cors(["*"])
        logger.info("storage.cors_applied_at_startup", provider=p, bucket=bucket)
    except Exception as exc:
        # Log the full chain: StorageError message + the underlying S3/botocore error.
        cause = getattr(exc, "__cause__", None) or exc
        logger.error(
            "storage.cors_apply_failed",
            provider=p,
            bucket=bucket,
            error=str(exc),
            cause=str(cause),
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("filenest.startup", env=settings.env, service=settings.service_name)

    # Apply CORS to the default managed bucket so browsers can PUT presigned URLs.
    await _apply_startup_cors()

    # Connect NATS and ensure the FILENEST_EVENTS stream exists
    await nats_core.connect()

    # Start the outbox worker — polls outbox_messages and publishes to NATS JetStream
    outbox_worker = OutboxWorker(AsyncSessionLocal)
    worker_task = outbox_worker.start()

    # Start the processing worker — pull consumer for file.uploaded events
    processing_worker = ProcessingWorker()
    processing_task = processing_worker.start()

    # Start the webhook worker — pull consumer for file.* events, delivers to customer URLs
    webhook_worker = WebhookWorker()
    webhook_task = webhook_worker.start()

    yield

    # Graceful shutdown: cancel workers before closing NATS
    processing_task.cancel()
    try:
        await processing_task
    except asyncio.CancelledError:
        pass

    webhook_task.cancel()
    try:
        await webhook_task
    except asyncio.CancelledError:
        pass

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await nats_core.disconnect()

    logger.info("filenest.shutdown")


app = FastAPI(
    title="FileNest API",
    version="1.0.0",
    description=(
        "FileNest — enterprise file infrastructure platform. "
        "Handles file upload, download, processing, search, and compliance. "
        "All auth is delegated to the IAM; this service verifies Bearer tokens."
    ),
    docs_url="/docs" if settings.is_dev else None,
    redoc_url="/redoc" if settings.is_dev else None,
    lifespan=lifespan,
)

# Per-project CORS must be added before exception handlers so preflight
# responses are returned before any middleware that might interfere.
app.add_middleware(PerProjectCORSMiddleware, sessionmaker=AsyncSessionLocal)

# Exception handlers — order matters: most specific first
app.add_exception_handler(FileNestError, filenest_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routers
app.include_router(health_router)
app.include_router(api_router)
