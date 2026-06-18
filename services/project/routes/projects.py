"""
services.project.routes.projects — HTTP handlers for project management.

Routes are thin: validate input, call ProjectService, return typed response.

All routes require authentication. Scope checks are performed inline.

Final paths (registered at /v1 prefix in router.py):
    POST  /v1/projects          create a new project
    GET   /v1/projects          list projects for the caller's organisation
    GET   /v1/projects/{id}     get a single project
"""
from fastapi import APIRouter, Depends

from shared.auth import require_scope

from ..dependencies import get_project_service
from ..schemas import CreateProjectRequest, ProjectListResponse, ProjectResponse
from ..service import ProjectService

router = APIRouter(tags=["Projects"])


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    svc: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Create a new project in the caller's organisation.

    The slug is derived from name if not provided. Slugs are unique within an
    organisation. Required scope: `projects:update`.
    """
    require_scope("projects:update")
    return await svc.create_project(body)


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    svc: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    """
    List all active projects in the caller's organisation.

    Required scope: `projects:read`.
    """
    require_scope("projects:read")
    return await svc.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    svc: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Fetch a single project by ID.

    Returns 404 if the project does not exist in the caller's organisation.
    Required scope: `projects:read`.
    """
    require_scope("projects:read")
    return await svc.get_project(project_id)
