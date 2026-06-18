"""
services.project.repository — Database access layer for the Project Service.

ProjectRepository is the ONLY place that issues SQL for projects. Every query
includes organization_id to prevent cross-tenant access.

Rules:
  - No business logic. Conditionals belong in service.py.
  - Use db.flush() after inserts.

Usage:
    from services.project.repository import ProjectRepository
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import NotFoundError
from shared.models.project import Project


class ProjectRepository:
    """
    Async repository for Project CRUD operations.

    Args:
        session: Active SQLAlchemy AsyncSession for the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> Project:
        """
        Insert a new Project row and flush to obtain the DB-assigned id.

        Args:
            **kwargs: Column values — must include organization_id, name, slug.

        Returns:
            The persisted Project with id populated.
        """
        record = Project(**kwargs)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get(self, project_id: str, organization_id: str) -> Project:
        """
        Fetch a single project by ID within the caller's organisation.

        Args:
            project_id:      UUID of the project.
            organization_id: Must match the record's organization_id.

        Returns:
            The matching Project.

        Raises:
            NotFoundError: If no matching record exists.
        """
        result = await self._session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundError(f"Project {project_id} not found")
        return record

    async def get_by_slug(self, slug: str, organization_id: str) -> Project | None:
        """
        Fetch a project by slug within the caller's organisation.

        Returns None if not found (used for uniqueness checks).
        """
        result = await self._session.execute(
            select(Project).where(
                Project.slug == slug,
                Project.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(self, organization_id: str) -> list[Project]:
        """
        Return all active projects for an organisation, newest first.

        Args:
            organization_id: Tenant filter.

        Returns:
            List of Project instances ordered by created_at descending.
        """
        result = await self._session.execute(
            select(Project)
            .where(
                Project.organization_id == organization_id,
                Project.is_active.is_(True),
            )
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())
