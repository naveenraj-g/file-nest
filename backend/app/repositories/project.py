"""
app.repositories.project — Database access layer for projects.

Every query includes organization_id to prevent cross-tenant leaks.
No business logic here — conditionals belong in services.

Usage:
    from app.repositories.project import ProjectRepository
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.project import Project


class ProjectRepository:
    """Async repository for Project CRUD. All queries are scoped to organization_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> Project:
        """Insert a new Project row and flush to get the DB-assigned id."""
        record = Project(**kwargs)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get(self, project_id: str, organization_id: str) -> Project:
        """
        Fetch a single project by ID within the caller's organisation.

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
        """Fetch a project by slug within the caller's organisation. Returns None if not found."""
        result = await self._session.execute(
            select(Project).where(
                Project.slug == slug,
                Project.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(self, organization_id: str) -> list[Project]:
        """Return all active projects for an organisation, newest first."""
        result = await self._session.execute(
            select(Project)
            .where(Project.organization_id == organization_id, Project.is_active.is_(True))
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())
