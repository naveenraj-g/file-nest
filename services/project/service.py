"""
services.project.service — Business logic for the Project Service.

ProjectService is the single place where all project business rules live. It
coordinates between ProjectRepository (DB) and any cross-service concerns.

Layer rules:
  - Service may call repository. No direct SQL.
  - All log calls include organization_id.

Usage:
    # Constructed via the get_project_service dependency — not directly.
    svc = ProjectService(session=session, ctx=ctx)
    result = await svc.create_project(request_body)
"""
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import TenantContext
from shared.exceptions import ConflictError
from shared.logging import get_logger

from .repository import ProjectRepository
from .schemas import CreateProjectRequest, ProjectListResponse, ProjectResponse

logger = get_logger(__name__)


class ProjectService:
    """
    Orchestrates project lifecycle operations for a single request.

    Args:
        session: Active DB session (owns commit/rollback).
        ctx:     Resolved caller identity. Only organization_id is required
                 for project operations — project_id may be None.
    """

    def __init__(self, session: AsyncSession, ctx: TenantContext) -> None:
        self._session = session
        self._ctx = ctx
        self._repo = ProjectRepository(session)

    async def create_project(self, req: CreateProjectRequest) -> ProjectResponse:
        """
        Create a new project within the caller's organisation.

        Enforces slug uniqueness within the organisation.

        Args:
            req: CreateProjectRequest with name, slug, description.

        Returns:
            ProjectResponse for the newly created project.

        Raises:
            ConflictError: If a project with the same slug already exists.
        """
        existing = await self._repo.get_by_slug(req.slug, self._ctx.organization_id)
        if existing is not None:
            raise ConflictError(
                f"A project with slug '{req.slug}' already exists in this organisation",
                detail={"slug": req.slug},
            )

        record = await self._repo.create(
            organization_id=self._ctx.organization_id,
            name=req.name,
            slug=req.slug,
            description=req.description,
        )
        await self._session.commit()

        logger.info(
            "project.created",
            project_id=record.id,
            slug=record.slug,
            organization_id=self._ctx.organization_id,
        )

        return self._to_response(record)

    async def get_project(self, project_id: str) -> ProjectResponse:
        """
        Return the full metadata for a single project.

        Args:
            project_id: UUID of the project.

        Returns:
            ProjectResponse.

        Raises:
            NotFoundError: If the project does not exist in this organisation.
        """
        record = await self._repo.get(project_id, self._ctx.organization_id)
        return self._to_response(record)

    async def list_projects(self) -> ProjectListResponse:
        """
        Return all active projects in the caller's organisation.

        Returns:
            ProjectListResponse with all projects.
        """
        records = await self._repo.list(self._ctx.organization_id)
        items = [self._to_response(r) for r in records]
        return ProjectListResponse(items=items, total=len(items))

    def _to_response(self, record) -> ProjectResponse:
        """Map a Project ORM object to its Pydantic response schema."""
        return ProjectResponse(
            id=record.id,
            organization_id=record.organization_id,
            name=record.name,
            slug=record.slug,
            description=record.description,
            storage_mode=record.storage_mode,
            is_active=record.is_active,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
