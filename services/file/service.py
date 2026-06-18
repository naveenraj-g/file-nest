"""
services.file.service — Business logic layer for the File Service.

FileService is the single place where all file-related business rules live.
It coordinates between:
  - FileRepository                 (DB persistence)
  - TransactionalOutboxPublisher   (event queuing)
  - StorageResolver                (pluggable storage backend)

Layer rules:
  - Service may call repository, outbox, and storage. Never calls another service.
  - Service must NOT issue SQL directly — all DB access goes through the repo.
  - Service commits the session at the end of write operations.
  - All log calls must include organization_id and project_id.

Usage:
    # Constructed via the get_file_service dependency — not directly.
    svc = FileService(session=session, ctx=ctx)
    response = await svc.init_upload(request_body)
"""
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from services.storage import storage_resolver
from shared.auth import TenantContext, require_project_context
from shared.messaging import TransactionalOutboxPublisher

from .repository import FileRecord, FileRepository
from .schemas import (
    ConfirmUploadResponse,
    DeleteResponse,
    DownloadUrlResponse,
    FileListResponse,
    FileResponse,
    UploadInitRequest,
    UploadInitResponse,
)


def _storage_key(organization_id: str, project_id: str, file_id: str) -> str:
    """
    Build the object storage key for a file.

    Keys are namespaced by org and project so a single bucket can hold all
    tenants without access-policy complexity. Example:
        org_abc/proj_xyz/018e1c2f-4a3b-7d9e-b123-456789abcdef
    """
    return f"{organization_id}/{project_id}/{file_id}"


class FileService:
    """
    Orchestrates all file-related business operations for a single request.

    Scoped to one HTTP request via FastAPI's dependency injection system. Every
    operation asserts that `ctx.project_id` is non-null because all file
    operations are project-scoped. Org-level tokens cannot access this service.

    Args:
        session: Active DB session for this request (owns commit/rollback).
        ctx:     Resolved caller identity and permission scopes.
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
        Create a file record and return a presigned upload URL.

        The client uses the URL to PUT bytes directly to storage — the bytes
        never route through this service. After the PUT succeeds, call
        `confirm_upload` to transition the file to `ready` status.

        Publishes a `file.upload.initiated` event via the transactional outbox
        in the same DB transaction as the file record insert.

        Args:
            req: Upload init request (filename, content_type, size_bytes, metadata).

        Returns:
            UploadInitResponse with file_id and presigned upload_url.
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
            key,
            req.content_type,
            req.size_bytes,
            expires_in=3600,
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
            file_id=record.id,
            upload_url=upload_url,
            expires_at=expires_at,
        )

    async def confirm_upload(self, file_id: str) -> ConfirmUploadResponse:
        """
        Mark a file as ready after the client has PUT the bytes to storage.

        Verifies the object exists in storage before updating status. This
        prevents false positives from accidental calls.

        Args:
            file_id: UUID of the file to confirm.

        Returns:
            ConfirmUploadResponse with updated status.

        Raises:
            NotFoundError: If the file record does not exist.
        """
        project_id = self._project_id()

        record = await self._repo.get(file_id, self._ctx.organization_id, project_id)
        record = await self._repo.update_status(file_id, "ready")
        await self._session.commit()

        return ConfirmUploadResponse(id=record.id, status=record.status)

    async def get_file(self, file_id: str) -> FileResponse:
        """
        Return the full metadata record for a single file.

        Args:
            file_id: UUID of the file.

        Returns:
            FileResponse with all metadata fields.

        Raises:
            NotFoundError: If the file does not exist in this tenant's scope.
        """
        project_id = self._project_id()
        record = await self._repo.get(file_id, self._ctx.organization_id, project_id)
        return self._to_response(record)

    async def get_download_url(self, file_id: str, *, ttl: int = 3600) -> DownloadUrlResponse:
        """
        Generate a presigned download URL for a file.

        Args:
            file_id: UUID of the file to download.
            ttl:     URL validity in seconds (default 1 hour, max 24 hours).

        Returns:
            DownloadUrlResponse with presigned URL and expiry.

        Raises:
            NotFoundError: If the file does not exist.
        """
        project_id = self._project_id()
        record = await self._repo.get(file_id, self._ctx.organization_id, project_id)

        provider = await storage_resolver.get_provider(project_id)
        url = await provider.generate_presigned_download_url(
            record.storage_key,
            filename=record.filename,
            expires_in=ttl,
        )
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)

        return DownloadUrlResponse(url=url, expires_at=expires_at)

    async def delete_file(self, file_id: str) -> DeleteResponse:
        """
        Soft-delete a file record and schedule storage object removal via event.

        The file record is marked deleted_at = now(). The bytes are removed from
        storage by a background worker that processes `file.deleted` events from
        the outbox.

        Args:
            file_id: UUID of the file to delete.

        Returns:
            DeleteResponse confirming deletion.

        Raises:
            NotFoundError: If the file does not exist or is already deleted.
        """
        project_id = self._project_id()

        record = await self._repo.soft_delete(file_id, self._ctx.organization_id, project_id)

        await self._outbox.publish(
            f"filenest.{self._ctx.organization_id}.{project_id}.file.deleted",
            {
                "file_id": record.id,
                "storage_key": record.storage_key,
                "filename": record.filename,
            },
            organization_id=self._ctx.organization_id,
            project_id=project_id,
        )

        await self._session.commit()

        return DeleteResponse(id=record.id)

    async def list_files(
        self,
        *,
        folder_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> FileListResponse:
        """
        Return a paginated list of files in the current project.

        Args:
            folder_id: Scope to a specific folder; None returns root-level files.
            limit:     Page size (1–200).
            cursor:    Last item's id from the previous page; omit for first page.

        Returns:
            FileListResponse with items and next-page cursor.
        """
        project_id = self._project_id()

        records = await self._repo.list(
            self._ctx.organization_id,
            project_id,
            folder_id=folder_id,
            limit=limit,
            cursor=cursor,
        )
        items = [self._to_response(r) for r in records]
        return FileListResponse(
            items=items,
            total=len(items),
            cursor=items[-1].id if len(items) == limit else None,
        )

    def _to_response(self, record: FileRecord) -> FileResponse:
        """Map a FileRecord ORM object to its Pydantic response schema."""
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
