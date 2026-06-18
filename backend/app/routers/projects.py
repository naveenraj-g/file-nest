"""
app.routers.projects — HTTP handlers for project management.

Routes are thin: validate input, call ProjectService, return typed response.

Routes registered at /v1 prefix:
    POST  /v1/projects           create a new project
    GET   /v1/projects           list projects for the caller's organisation
    GET   /v1/projects/{id}      get a single project
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TenantContext, authenticate_request, require_scope
from app.core.database import get_db
from app.schemas.project import CreateProjectRequest, ProjectListResponse, ProjectResponse
from app.services.project import ProjectService

router = APIRouter(tags=["Projects"])


def _get_service(
    session: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(authenticate_request),
) -> ProjectService:
    return ProjectService(session=session, ctx=ctx)


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    svc: ProjectService = Depends(_get_service),
) -> ProjectResponse:
    """Create a new project in the caller's organisation. Scope: projects:update."""
    require_scope(svc._ctx, "projects:update")
    return await svc.create_project(body)


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    svc: ProjectService = Depends(_get_service),
) -> ProjectListResponse:
    """List all active projects in the caller's organisation. Scope: projects:read."""
    require_scope(svc._ctx, "projects:read")
    return await svc.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    svc: ProjectService = Depends(_get_service),
) -> ProjectResponse:
    """Fetch a single project by ID. Scope: projects:read."""
    require_scope(svc._ctx, "projects:read")
    return await svc.get_project(project_id)
