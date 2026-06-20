"""
app.main — FileNest FastAPI application factory.

Single-process FastAPI backend handling file operations, project management,
and storage abstraction. Authentication is delegated entirely to the IAM
(BetterAuth) — this service only verifies tokens, never issues them.

Run locally:
    uv run uvicorn app.main:app --reload --port 8000

API docs: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from sqlalchemy.exc import IntegrityError

from app.errors.base import FileNestError
from app.errors.handlers import (
    filenest_error_handler,
    http_exception_handler,
    integrity_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.di.container import Container
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
    yield
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
