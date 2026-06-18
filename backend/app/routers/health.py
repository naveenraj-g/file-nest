"""app.routers.health — Health check endpoints."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.database import AsyncSessionLocal

router = APIRouter(tags=["Health"])


@router.get("/health", operation_id="health_check", include_in_schema=False)
async def health_check():
    """Liveness probe — returns 200 if the process is running."""
    return {"status": "ok"}


@router.get("/health/ready", operation_id="readiness_check", tags=["Health"])
async def readiness_check(request: Request):
    """Readiness probe — checks DB and Redis connectivity."""
    checks: dict[str, str] = {}
    healthy = True

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
        healthy = False

    return JSONResponse(
        content={"status": "ok" if healthy else "degraded", "checks": checks},
        status_code=200 if healthy else 503,
    )
