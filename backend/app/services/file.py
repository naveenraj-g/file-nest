"""
app.services.file — Business logic for file management.

All file business rules live here. Coordinates with FileRepository (DB),
TransactionalOutboxPublisher (events), and StorageResolver (storage backend).

Usage:
    svc = FileService(session=session, ctx=ctx)
    result = await svc.init_upload(request_body)
"""
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TenantContext, require_project_context
from app.core.messaging import TransactionalOutboxPublisher
from app.repositories.file import FileRepository
from app.schemas.file import (
    ConfirmUploadResponse,
    DeleteResponse,
    DownloadUrlResponse,
    FileListResponse,
    FileResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from app.storage.resolver import storage_resolver


def _storage_key(organization_id: str, project_id: str, file_id: str) -> str:
    """Build the object storage key: org/project/file_id."""
    return f"{organization_id}/{project_id}/{file_id}"


class FileService:
    """
    Orchestrates file operations for a single request.

    All operations assert that ctx.project_id is non-null — file operations
    are always project-scoped.

    Args:
        session: Active DB session (owns commit/rollback).
        ctx:     Resolved caller identity.
    """

    def __init__(self, session: AsyncSession, ctx: TenantContext) -> None:
        self._session = session
        self._ctx = ctx
        self._repo = FileRepository(session)
        self._outbox = TransactionalOutboxPublisher(session)

    def _project_id(self) -> str:
        """Return project_id or raise 400 if this is an org-level token."""
        return require_project_context(self._ctx)

    async def init_upload(self, req: UploadInitRequest) -> UploadInitResponse:
        """
        Create a file record and return a presigned PUT URL.

        The client PUTs bytes directly to storage — bytes never route through
        this service. Call confirm_upload after PUT succeeds.
        """
        project_id = self._project_id()

        record = await self._repo.create(
            organization_id=self._ctx.organization_id,
            project_id=project_id,
            filename=req.filename,
            content_type=req.content_type,
            size_bytes=req.size_bytes,
            folder_id=req.folder_id,
            metadata_json=json.dumps(req.metadata),
        )

        key = _storage_key(self._ctx.organization_id, project_id, record.id)
        record.storage_key = key

        provider = await storage_resolver.get_provider(project_id)
        upload_url = await provider.generate_presigned_upload_url(
            key, req.content_type, req.size_bytes, expires_in=3600,
        )
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await self._outbox.publish(
            f"filenest.{self._ctx.organization_id}.{project_id}.file.upload.initiated",
            {"file_id": record.id, "filename": req.filename, "size_bytes": req.size_bytes},
            organization_id=self._ctx.organization_id,
            project_id=project_id,
        )

        await self._session.commit()

        return UploadInitResponse(
            file_id=record.id, upload_url=upload_url, expires_at=expires_at,
        )

    async def confirm_upload(self, file_id: str) -> ConfirmUploadResponse:
        """Mark a file as ready after the client has PUT the bytes to storage."""
        project_id = self._project_id()
        await self._repo.get(file_id, self._ctx.organization_id, project_id)
        record = await self._repo.update_status(file_id, "ready")
        await self._session.commit()
        return ConfirmUploadResponse(id=record.id, status=record.status)

    async def get_file(self, file_id: str) -> FileResponse:
        """Return the full metadata record for a single file."""
        project_id = self._project_id()
        record = await self._repo.get(file_id, self._ctx.organization_id, project_id)
        return self._to_response(record)

    async def get_download_url(self, file_id: str, *, ttl: int = 3600) -> DownloadUrlResponse:
        """Generate a presigned download URL for a file."""
        project_id = self._project_id()
        record = await self._repo.get(file_id, self._ctx.organization_id, project_id)

        provider = await storage_resolver.get_provider(project_id)
        url = await provider.generate_presigned_download_url(
            record.storage_key, filename=record.filename, expires_in=ttl,
        )
        return DownloadUrlResponse(url=url, expires_at=datetime.now(UTC) + timedelta(seconds=ttl))

    async def delete_file(self, file_id: str) -> DeleteResponse:
        """Soft-delete a file. Bytes removed from storage via background event."""
        project_id = self._project_id()
        record = await self._repo.soft_delete(file_id, self._ctx.organization_id, project_id)

        await self._outbox.publish(
            f"filenest.{self._ctx.organization_id}.{project_id}.file.deleted",
            {"file_id": record.id, "storage_key": record.storage_key, "filename": record.filename},
            organization_id=self._ctx.organization_id,
            project_id=project_id,
        )

        await self._session.commit()
        return DeleteResponse(id=record.id)

    async def list_files(
        self, *, folder_id: str | None = None, limit: int = 50, cursor: str | None = None,
    ) -> FileListResponse:
        """Return a cursor-paginated list of files in the current project."""
        project_id = self._project_id()
        records = await self._repo.list(
            self._ctx.organization_id, project_id,
            folder_id=folder_id, limit=limit, cursor=cursor,
        )
        items = [self._to_response(r) for r in records]
        return FileListResponse(
            items=items, total=len(items),
            cursor=items[-1].id if len(items) == limit else None,
        )

    def _to_response(self, record) -> FileResponse:
        return FileResponse(
            id=record.id,
            organization_id=record.organization_id,
            project_id=record.project_id,
            filename=record.filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            status=record.status,
            storage_key=record.storage_key or "",
            folder_id=record.folder_id,
            metadata=json.loads(record.metadata_json),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
