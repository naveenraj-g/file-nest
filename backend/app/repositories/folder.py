"""
app.repositories.folder — Database access layer for folders.

Every query is scoped to organization_id + project_id to prevent cross-tenant
leaks. Soft-deleted folders (deleted_at IS NOT NULL) are excluded from all reads.

Usage:
    from app.repositories.folder import FolderRepository
"""
from datetime import UTC, datetime

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.file import File
from app.models.folder import Folder


class FolderRepository:
    """Async repository for Folder CRUD. All queries are tenant-scoped."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        organization_id: str,
        project_id: str,
        name: str,
        path: str,
        parent_folder_id: str | None,
    ) -> Folder:
        """
        Insert a new Folder row and flush to get the DB-assigned id.

        path must be pre-computed by the caller (FolderService) before calling create.
        """
        record = Folder(
            organization_id=organization_id,
            project_id=project_id,
            name=name,
            path=path,
            parent_folder_id=parent_folder_id,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get(
        self, folder_id: str, organization_id: str, project_id: str
    ) -> Folder:
        """
        Fetch a single active folder by ID within the caller's tenant scope.

        Raises:
            NotFoundError: If the folder does not exist or is soft-deleted.
        """
        result = await self._session.execute(
            select(Folder).where(
                Folder.id == folder_id,
                Folder.organization_id == organization_id,
                Folder.project_id == project_id,
                Folder.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundError(f"Folder {folder_id} not found")
        return record

    async def list(self, organization_id: str, project_id: str) -> list[Folder]:
        """
        Return all active folders in the project, ordered by path (breadth-first).
        """
        result = await self._session.execute(
            select(Folder).where(
                Folder.organization_id == organization_id,
                Folder.project_id == project_id,
                Folder.deleted_at.is_(None),
            ).order_by(Folder.path)
        )
        return list(result.scalars().all())

    async def has_subfolders(
        self, folder_id: str, organization_id: str, project_id: str
    ) -> bool:
        """Return True if any active subfolder exists directly under this folder."""
        result = await self._session.execute(
            select(
                exists().where(
                    Folder.parent_folder_id == folder_id,
                    Folder.organization_id == organization_id,
                    Folder.project_id == project_id,
                    Folder.deleted_at.is_(None),
                )
            )
        )
        return bool(result.scalar())

    async def has_files(
        self, folder_id: str, organization_id: str, project_id: str
    ) -> bool:
        """Return True if any active (non-deleted) file lives in this folder."""
        result = await self._session.execute(
            select(
                exists().where(
                    File.folder_id == folder_id,
                    File.organization_id == organization_id,
                    File.project_id == project_id,
                    File.deleted_at.is_(None),
                )
            )
        )
        return bool(result.scalar())

    async def soft_delete(
        self, folder_id: str, organization_id: str, project_id: str
    ) -> Folder:
        """
        Mark a folder as deleted by setting deleted_at = now().

        Raises:
            NotFoundError: If the folder does not exist or is already deleted.
        """
        record = await self.get(folder_id, organization_id, project_id)
        record.deleted_at = datetime.now(UTC)
        return record
