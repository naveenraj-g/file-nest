"""
app.services.project — Business logic for project management.

All project business rules live here. Coordinates with ProjectRepository (DB)
and StorageConfigRepository (auto-creates a storage config on project creation).
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
from app.repositories.storage_config import StorageConfigRepository


from app.schemas.project import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    UpdateProjectRequest,
)

logger = get_logger(__name__)


class ProjectService:
    """
    Orchestrates project lifecycle operations for a single request.

    Args:
        session: Active DB session (owns commit/rollback).
        ctx:     Resolved caller identity. Only organization_id is required.
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: ProjectRepository,
        storage_repo: StorageConfigRepository,
        ctx: TenantContext,
    ) -> None:
        self._session = session
        self._ctx = ctx
        self._repo = repo
        self._storage_repo = storage_repo

    async def create_project(self, req: CreateProjectRequest) -> ProjectResponse:
        """
        Create a new project and its default StorageConfig in a single transaction.

        A StorageConfig row is always created alongside the project so the storage
        resolver has a row to read on the first upload. For managed mode the config
        holds no credentials — the platform defaults from settings are used.

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
            storage_mode=req.storage_mode,
            storage_provider=req.storage_provider,
        )

        # Auto-create the default storage config in the same transaction.
        # Managed configs are immediately active. BYOB configs start as
        # pending_verification — the full BYOB credential flow is Phase 7.
        await self._storage_repo.create(
            organization_id=self._ctx.organization_id,
            project_id=record.id,
            environment="production",
            storage_mode=req.storage_mode,
            provider=req.storage_provider,
            status="active" if req.storage_mode == "managed" else "pending_verification",
        )

        await self._session.commit()

        logger.info(
            "project.created",
            project_id=record.id,
            slug=record.slug,
            storage_mode=req.storage_mode,
            storage_provider=req.storage_provider,
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

    async def update_project(self, project_id: str, req: UpdateProjectRequest) -> ProjectResponse:
        """
        Apply a partial update to a project.

        Only fields present (non-None) in the request body are written.

        Raises:
            NotFoundError: If the project does not exist.
        """
        record = await self._repo.update(
            project_id,
            self._ctx.organization_id,
            name=req.name,
            description=req.description,
            versioning_enabled=req.versioning_enabled,
            ocr_enabled=req.ocr_enabled,
        )
        await self._session.commit()

        logger.info(
            "project.updated",
            project_id=project_id,
            organization_id=self._ctx.organization_id,
        )

        return self._to_response(record)

    async def delete_project(self, project_id: str) -> None:
        """
        Soft-delete a project. Files and storage config are retained.

        Raises:
            NotFoundError: If the project does not exist.
        """
        await self._repo.soft_delete(project_id, self._ctx.organization_id)
        await self._session.commit()

        logger.info(
            "project.deleted",
            project_id=project_id,
            organization_id=self._ctx.organization_id,
        )

    def _to_response(self, record) -> ProjectResponse:
        return ProjectResponse(
            id=record.id,
            organization_id=record.organization_id,
            name=record.name,
            slug=record.slug,
            description=record.description,
            storage_mode=record.storage_mode,
            storage_provider=record.storage_provider,
            versioning_enabled=record.versioning_enabled,
            ocr_enabled=record.ocr_enabled,
            is_active=record.is_active,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
