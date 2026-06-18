"""
services.identity.main — FastAPI application factory for the Identity Service.

The Identity Service manages API keys. It runs on port 8002 in local development.

Startup sequence (lifespan):
  1. configure_logging() — structlog setup
  2. Yield control to FastAPI
  3. close_redis() — drain Redis connection pool on shutdown

Commands:
    Run locally:  just identity
    API docs:     http://localhost:8002/docs
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
    Construct and configure the Identity Service FastAPI application.

    Registers:
      - Global FileNestError handler → standard JSON error envelope
      - All identity-service routes under the /v1 prefix

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(
        title="FileNest — Identity Service",
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

    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        """Liveness probe — returns 200 when the service is up."""
        return {"status": "ok", "service": "identity"}

    app.include_router(router, prefix="/v1")

    return app


app = create_app()
