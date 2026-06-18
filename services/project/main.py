"""
services.project.main — FastAPI application factory for the Project Service.

The Project Service manages project lifecycle (create, read, list). It runs on
port 8003 in local development.

Commands:
    Run locally:  just project
    API docs:     http://localhost:8003/docs
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
    Construct and configure the Project Service FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(
        title="FileNest — Project Service",
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
        return {"status": "ok", "service": "project"}

    app.include_router(router, prefix="/v1")

    return app


app = create_app()
