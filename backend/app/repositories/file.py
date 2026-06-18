"""
app.repositories.file — Database access layer for files.

Every query includes organization_id + project_id to prevent cross-tenant leaks.
Soft-deleted files (deleted_at IS NOT NULL) are excluded from all queries.

Usage:
    from app.repositories.file import FileRepository
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.file import File


class FileRepository:
    """Async repository for File CRUD. All queries are tenant-scoped."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> File:
        """Insert a new File row and flush to get the DB-assigned id."""
        record = File(**kwargs)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get(self, file_id: str, organization_id: str, project_id: str) -> File:
        """
        Fetch a single file by ID within the caller's tenant scope.

        Raises:
            NotFoundError: If the file does not exist or is deleted.
        """
        result = await self._session.execute(
            select(File).where(
                File.id == file_id,
                File.organization_id == organization_id,
                File.project_id == project_id,
                File.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundError(f"File {file_id} not found")
        return record

    async def list(
        self,
        organization_id: str,
        project_id: str,
        *,
        folder_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[File]:
        """
        Return a cursor-paginated list of files, newest first.

        Args:
            folder_id: Scope to a folder; None returns root-level files.
            limit:     Page size.
            cursor:    Last item's id from previous page.
        """
        stmt = select(File).where(
            File.organization_id == organization_id,
            File.project_id == project_id,
            File.deleted_at.is_(None),
        )
        if folder_id is not None:
            stmt = stmt.where(File.folder_id == folder_id)
        if cursor:
            stmt = stmt.where(File.id > cursor)
        stmt = stmt.order_by(File.created_at.desc()).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, file_id: str, status: str) -> File:
        """
        Update a file's status and bump updated_at.

        Raises:
            NotFoundError: If the file does not exist.
        """
        record = await self._session.get(File, file_id)
        if record is None:
            raise NotFoundError(f"File {file_id} not found")
        record.status = status
        record.updated_at = datetime.now(UTC)
        return record

    async def soft_delete(self, file_id: str, organization_id: str, project_id: str) -> File:
        """
        Mark a file as deleted by setting deleted_at = now().

        Raises:
            NotFoundError: If the file does not exist or is already deleted.
        """
        record = await self.get(file_id, organization_id, project_id)
        record.deleted_at = datetime.now(UTC)
        record.updated_at = datetime.now(UTC)
        return record
