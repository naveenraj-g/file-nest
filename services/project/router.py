"""
services.project.router — Route registration for the Project Service.

Usage:
    from services.project.router import router
    app.include_router(router, prefix="/v1")
"""
from fastapi import APIRouter

from .routes.projects import router as projects_router

router = APIRouter()
router.include_router(projects_router)
