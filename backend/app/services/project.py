"""
app.services.project — Business logic for project management.

All project business rules live here. Coordinates with ProjectRepository (DB).
No direct SQL, no storage calls, no HTTP calls.

Usage:
    svc = ProjectService(session=session, ctx=ctx)
    result = await svc.create_project(request_body)
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TenantContext
from app.core.logging import get_logger
from app.errors import ConflictError
from app.repositories.project import ProjectRepository
from app.schemas.project import CreateProjectRequest, ProjectListResponse, ProjectResponse

logger = get_logger(__name__)


class ProjectService:
    """
    Orchestrates project lifecycle operations for a single request.

    Args:
        session: Active DB session (owns commit/rollback).
        ctx:     Resolved caller identity. Only organization_id is required.
    """

    def __init__(self, session: AsyncSession, ctx: TenantContext) -> None:
        self._session = session
        self._ctx = ctx
        self._repo = ProjectRepository(session)

    async def create_project(self, req: CreateProjectRequest) -> ProjectResponse:
        """
        Create a new project within the caller's organisation.

        Raises:
            ConflictError: If a project with the same slug already exists.
        """
        existing = await self._repo.get_by_slug(req.slug, self._ctx.organization_id)
        if existing is not None:
            raise ConflictError(
                f"A project with slug '{req.slug}' already exists",
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

        Raises:
            NotFoundError: If the project does not exist in this organisation.
        """
        record = await self._repo.get(project_id, self._ctx.organization_id)
        return self._to_response(record)

    async def list_projects(self) -> ProjectListResponse:
        """Return all active projects in the caller's organisation."""
        records = await self._repo.list(self._ctx.organization_id)
        items = [self._to_response(r) for r in records]
        return ProjectListResponse(items=items, total=len(items))

    def _to_response(self, record) -> ProjectResponse:
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
