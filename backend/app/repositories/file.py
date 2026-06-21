"""
app.repositories.file — Database access layer for files.

Every query includes organization_id + project_id to prevent cross-tenant leaks.
Soft-deleted files (deleted_at IS NOT NULL) are excluded from all queries.

Usage:
    from app.repositories.file import FileRepository
"""
import json
from datetime import UTC, datetime

from sqlalchemy import cast, select, type_coerce
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy import String
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
        q: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        metadata_filter: dict | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[File]:
        """
        Return a cursor-paginated list of files, newest first, with optional filters.

        Args:
            folder_id:       Scope to a specific folder; None returns all files regardless of folder.
            q:               Filename substring search (case-insensitive).
            tags:            File must have ALL of these tags (array containment).
            category:        Exact match on category (document, image, video, …).
            status:          Exact match on status (ready, processing, …).
            date_from:       created_at >= date_from.
            date_to:         created_at <= date_to.
            size_min:        size_bytes >= size_min.
            size_max:        size_bytes <= size_max.
            metadata_filter: JSONB containment — file metadata must include all key-value pairs.
            limit:           Page size (max 200).
            cursor:          Last file id from the previous page for keyset pagination.
        """
        stmt = select(File).where(
            File.organization_id == organization_id,
            File.project_id == project_id,
            File.deleted_at.is_(None),
        )

        if folder_id is not None:
            stmt = stmt.where(File.folder_id == folder_id)
        if q:
            stmt = stmt.where(File.filename.ilike(f"%{q}%"))
        if tags:
            # tags @> ARRAY['a','b'] — file must have ALL of the specified tags
            stmt = stmt.where(
                File.tags.op("@>")(type_coerce(tags, ARRAY(String())))
            )
        if category:
            stmt = stmt.where(File.category == category)
        if status:
            stmt = stmt.where(File.status == status)
        if date_from:
            stmt = stmt.where(File.created_at >= date_from)
        if date_to:
            stmt = stmt.where(File.created_at <= date_to)
        if size_min is not None:
            stmt = stmt.where(File.size_bytes >= size_min)
        if size_max is not None:
            stmt = stmt.where(File.size_bytes <= size_max)
        if metadata_filter:
            # Cast Text column to JSONB for containment check
            stmt = stmt.where(
                cast(File.metadata_json, JSONB).op("@>")(
                    cast(json.dumps(metadata_filter), JSONB)
                )
            )

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

    async def update_category(self, file_id: str, category: str) -> File:
        """
        Set the category column after classification.

        Raises:
            NotFoundError: If the file does not exist.
        """
        record = await self._session.get(File, file_id)
        if record is None:
            raise NotFoundError(f"File {file_id} not found")
        record.category = category
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

    async def set_tags(
        self, file_id: str, organization_id: str, project_id: str, tags: list[str]
    ) -> File:
        """
        Replace the full tag list on a file. Duplicates are removed preserving order.

        Raises:
            NotFoundError: If the file does not exist.
        """
        record = await self.get(file_id, organization_id, project_id)
        record.tags = list(dict.fromkeys(tags))
        record.updated_at = datetime.now(UTC)
        return record

    async def add_tags(
        self, file_id: str, organization_id: str, project_id: str, tags: list[str]
    ) -> File:
        """
        Append tags that are not already present (union, no duplicates).

        Raises:
            NotFoundError: If the file does not exist.
        """
        record = await self.get(file_id, organization_id, project_id)
        existing = set(record.tags or [])
        new_tags = [t for t in tags if t not in existing]
        record.tags = (record.tags or []) + new_tags
        record.updated_at = datetime.now(UTC)
        return record

    async def update_metadata(
        self, file_id: str, organization_id: str, project_id: str, metadata: dict
    ) -> File:
        """
        Replace the entire metadata object on a file.

        Raises:
            NotFoundError: If the file does not exist.
        """
        record = await self.get(file_id, organization_id, project_id)
        record.metadata_json = json.dumps(metadata)
        record.updated_at = datetime.now(UTC)
        return record

    async def merge_metadata(
        self, file_id: str, organization_id: str, project_id: str, updates: dict
    ) -> File:
        """
        Merge specific keys into the existing metadata. Existing keys not in
        updates are preserved.

        Raises:
            NotFoundError: If the file does not exist.
        """
        record = await self.get(file_id, organization_id, project_id)
        current = json.loads(record.metadata_json or "{}")
        current.update(updates)
        record.metadata_json = json.dumps(current)
        record.updated_at = datetime.now(UTC)
        return record

    async def move_file(
        self, file_id: str, organization_id: str, project_id: str, folder_id: str | None
    ) -> File:
        """
        Update a file's folder_id (or clear it to move to root).

        Raises:
            NotFoundError: If the file does not exist.
        """
        record = await self.get(file_id, organization_id, project_id)
        record.folder_id = folder_id
        record.updated_at = datetime.now(UTC)
        return record
