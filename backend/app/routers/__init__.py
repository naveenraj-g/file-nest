"""app.routers — All API routers aggregated here."""
from fastapi import APIRouter

from .files import router as files_router
from .project_config import router as project_config_router
from .projects import router as projects_router
from .storage import router as storage_router
from .webhooks import router as webhooks_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(projects_router)
api_router.include_router(project_config_router)
api_router.include_router(files_router)
api_router.include_router(storage_router)
api_router.include_router(webhooks_router)
