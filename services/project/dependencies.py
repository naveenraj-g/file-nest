"""
services.project.dependencies — FastAPI dependency wiring for the Project Service.

Usage:
    from services.project.dependencies import get_project_service
    from services.project.service import ProjectService
    from fastapi import Depends

    @router.post("/projects")
    async def create_project(svc: ProjectService = Depends(get_project_service)):
        ...
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import TenantContext, authenticate_request
from shared.database import get_db

from .service import ProjectService


async def get_project_service(
    session: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(authenticate_request),
) -> ProjectService:
    """Construct a ProjectService bound to the current request's session and tenant."""
    return ProjectService(session=session, ctx=ctx)
