"""
services.file.main — FastAPI application factory for the File Service.

The File Service handles file upload initiation, metadata persistence, download
URL generation, and file listing. It is the primary service for Phase 1 and
runs on port 8001 in local development.

Startup sequence (lifespan):
  1. configure_logging() — structlog setup
  2. Yield control to FastAPI (app is now serving requests)
  3. close_redis() — drain the Redis connection pool on shutdown

All domain errors (FileNestError subclasses) are caught by the global handler
and serialised to the standard JSON error envelope before reaching the client.
FastAPI's built-in validation errors (422) are not overridden.

Commands:
    Run locally:   just file
    API docs:      http://localhost:8001/docs
    Health check:  GET /v1/health  (implicit via FastAPI startup)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.cache import close_redis
from shared.exceptions import FileNestError
from shared.logging import configure_logging

from .router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure shared resources on startup and release them on shutdown."""
    configure_logging()
    yield
    await close_redis()


def create_app() -> FastAPI:
    """
    Construct and configure the File Service FastAPI application.

    Registers:
      - Global FileNestError handler → standard JSON error envelope
      - All file-service routes under the /v1 prefix

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(
        title="FileNest — File Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    @app.exception_handler(FileNestError)
    async def filenest_error_handler(request: Request, exc: FileNestError) -> JSONResponse:
        """Convert any FileNestError subclass into the standard error envelope."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message, "detail": exc.detail},
        )

    app.include_router(router, prefix="/v1")

    return app


# Module-level app instance used by uvicorn: `uvicorn services.file.main:app`
app = create_app()
