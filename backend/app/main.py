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

# Import all models so Alembic can discover the full schema in one pass
import app.models  # noqa: F401
import app.core.messaging  # noqa: F401

configure_logging()
logger = get_logger(__name__)

container = Container()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("filenest.startup", env=settings.env, service=settings.service_name)

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

# Exception handlers — order matters: most specific first
app.add_exception_handler(FileNestError, filenest_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routers
app.include_router(health_router)
app.include_router(api_router)
