"""
app.repositories.project — Database access layer for projects.

Every query includes organization_id to prevent cross-tenant leaks.
No business logic here — conditionals belong in services.

Usage:
    from app.repositories.project import ProjectRepository
"""
from datetime import UTC, datetime

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
        Fetch a single active project by ID within the caller's organisation.

        Raises:
            NotFoundError: If no matching record exists or it is soft-deleted.
        """
        result = await self._session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
                Project.deleted_at.is_(None),
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
                Project.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list(self, organization_id: str) -> list[Project]:
        """Return all active non-deleted projects for an organisation, newest first."""
        result = await self._session.execute(
            select(Project)
            .where(
                Project.organization_id == organization_id,
                Project.is_active.is_(True),
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, project_id: str, organization_id: str, **fields) -> Project:
        """
        Apply a partial update to a project. Only non-None values are applied.

        Args:
            fields: Keyword arguments matching Project column names.

        Raises:
            NotFoundError: If the project does not exist.
        """
        record = await self.get(project_id, organization_id)
        for key, value in fields.items():
            if value is not None:
                setattr(record, key, value)
        record.updated_at = datetime.now(UTC)
        return record

    async def soft_delete(self, project_id: str, organization_id: str) -> Project:
        """
        Soft-delete a project by setting deleted_at and flipping is_active to False.

        Raises:
            NotFoundError: If the project does not exist or is already deleted.
        """
        record = await self.get(project_id, organization_id)
        record.deleted_at = datetime.now(UTC)
        record.is_active = False
        record.updated_at = datetime.now(UTC)
        return record
