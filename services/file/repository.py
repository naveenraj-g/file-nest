"""
services.file.repository — Database access layer for the File Service.

FileRepository is the ONLY place in the file service that issues SQL. It
enforces two mandatory invariants on every query:
  1. organization_id filter — prevents cross-tenant data leaks
  2. project_id filter      — scopes results to the requested project

Rules for this layer:
  - No business logic. If you find yourself adding an `if`, it belongs in
    service.py instead.
  - Use `db.flush()` (not `db.commit()`) after inserts — the session context
    manager in get_db() commits on clean exit.
  - Never import or call storage providers, message publishers, or external APIs.

Usage:
    from services.file.repository import FileRepository

    repo = FileRepository(session)
    record = await repo.get(file_id, org_id, project_id)
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import Base
from shared.exceptions import NotFoundError


class FileRecord(Base):
    """
    ORM model for the `files` table.

    Represents a single file's metadata. The actual bytes live in object
    storage and are referenced by `storage_key`. The `status` column drives
    the file's availability lifecycle (see FileStatus in schemas.py).
    """

    __tablename__ = "files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
    storage_key = Column(String, nullable=True)     # Set after upload is confirmed
    folder_id = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")   # JSON blob
    deleted_at = Column(DateTime(timezone=True), nullable=True)   # Set on soft delete
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class FileRepository:
    """
    Async repository for FileRecord CRUD operations.

    Every method requires organization_id and project_id (or receives them from
    the constructor) and includes them in all queries as mandatory filters.

    Args:
        session: Active SQLAlchemy AsyncSession for the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> FileRecord:
        """
        Insert a new FileRecord row and flush to obtain the DB-assigned id.

        Args:
            **kwargs: Column values — must include organization_id and project_id.

        Returns:
            The persisted FileRecord with id populated.
        """
        record = FileRecord(**kwargs)
        self._session.add(record)
        await self._session.flush()   # gets the id without committing
        return record

    async def get(self, file_id: str, organization_id: str, project_id: str) -> FileRecord:
        """
        Fetch a single file record by ID within the caller's tenant scope.

        Args:
            file_id:         UUID of the file.
            organization_id: Must match the record's organization_id.
            project_id:      Must match the record's project_id.

        Returns:
            The matching FileRecord.

        Raises:
            NotFoundError: If no matching record exists (including cross-tenant misses).
        """
        result = await self._session.execute(
            select(FileRecord).where(
                FileRecord.id == file_id,
                FileRecord.organization_id == organization_id,
                FileRecord.project_id == project_id,
                FileRecord.deleted_at.is_(None),
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
    ) -> list[FileRecord]:
        """
        Return a page of file records ordered by created_at descending.

        Cursor-based pagination: pass the last item's id as `cursor` to fetch
        the next page. The cursor is compared as a string (UUID), not a timestamp,
        so the ordering is consistent even when two files are created in the same
        millisecond.

        Args:
            organization_id: Tenant filter.
            project_id:      Project filter.
            folder_id:       Optional folder scope; None returns root-level files.
            limit:           Maximum rows to return (default 50, max 200).
            cursor:          Last seen file id for keyset pagination.

        Returns:
            List of FileRecord instances, newest first.
        """
        stmt = select(FileRecord).where(
            FileRecord.organization_id == organization_id,
            FileRecord.project_id == project_id,
            FileRecord.deleted_at.is_(None),
        )
        if folder_id is not None:
            stmt = stmt.where(FileRecord.folder_id == folder_id)
        if cursor:
            stmt = stmt.where(FileRecord.id > cursor)
        stmt = stmt.order_by(FileRecord.created_at.desc()).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(
        self, file_id: str, organization_id: str, project_id: str
    ) -> FileRecord:
        """
        Mark a file as deleted by setting deleted_at to the current timestamp.

        The row is retained for audit purposes. Subsequent calls to `get` and
        `list` will exclude deleted files.

        Args:
            file_id:         UUID of the file to delete.
            organization_id: Tenant filter.
            project_id:      Project filter.

        Returns:
            The updated FileRecord with deleted_at set.

        Raises:
            NotFoundError: If the file does not exist or is already deleted.
        """
        record = await self.get(file_id, organization_id, project_id)
        record.deleted_at = datetime.now(UTC)
        record.updated_at = datetime.now(UTC)
        return record

    async def update_status(self, file_id: str, status: str) -> FileRecord:
        """
        Update a file's status field and bump updated_at.

        Used by the processing pipeline to transition files through their
        lifecycle (pending → processing → ready / failed / quarantined).

        Args:
            file_id: UUID of the file to update.
            status:  New status string (see FileStatus enum).

        Returns:
            The updated FileRecord.

        Raises:
            NotFoundError: If file_id does not exist.
        """
        record = await self._session.get(FileRecord, file_id)
        if record is None:
            raise NotFoundError(f"File {file_id} not found")
        record.status = status
        record.updated_at = datetime.now(UTC)
        return record
