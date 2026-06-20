"""
app.services.file — Business logic for file management.

All file business rules live here. Coordinates with FileRepository (DB),
ProjectConfigRepository (per-project feature flags), TransactionalOutboxPublisher
(events), and StorageResolver (storage backend).

confirm_upload flow (Phase 2):
  - virus_scan_enabled = true  → status=processing, emit file.uploaded
    (ProcessingWorker picks this up and runs stages)
  - virus_scan_enabled = false → status=ready, emit file.ready directly

project_id always comes from the URL path parameter, not the token. The router
validates that a project-scoped token's project_id matches the URL before
constructing this service.

Usage:
    svc = FileService(session=session, repo=repo, config_repo=config_repo,
                      outbox=outbox, ctx=ctx, project_id=project_id)
    result = await svc.init_upload(request_body)
"""
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TenantContext
from app.core.messaging import TransactionalOutboxPublisher
from app.repositories.file import FileRepository
from app.repositories.project_config import ProjectConfigRepository

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

    project_id is explicit (from the URL path) rather than read from ctx so that
    org-level tokens can operate on any project within the org.

    Args:
        session:     Active DB session (owns commit/rollback).
        repo:        FileRepository for file CRUD.
        config_repo: ProjectConfigRepository for feature flag lookups.
        outbox:      TransactionalOutboxPublisher for event enqueuing.
        ctx:         Resolved caller identity.
        project_id:  Project UUID from the URL path parameter.
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: FileRepository,
        config_repo: ProjectConfigRepository,
        outbox: TransactionalOutboxPublisher,
        ctx: TenantContext,
        project_id: str,
    ) -> None:
        self._session = session
        self._ctx = ctx
        self._project_id = project_id
        self._repo = repo
        self._config_repo = config_repo
        self._outbox = outbox

    async def init_upload(self, req: UploadInitRequest) -> UploadInitResponse:
        """
        Create a file record and return a presigned PUT URL.

        The client PUTs bytes directly to storage — bytes never route through
        this service. Call confirm_upload after the PUT succeeds.
        """
        record = await self._repo.create(
            organization_id=self._ctx.organization_id,
            project_id=self._project_id,
            filename=req.filename,
            content_type=req.content_type,
            size_bytes=req.size_bytes,
            folder_id=req.folder_id,
            metadata_json=json.dumps(req.metadata),
        )

        key = _storage_key(self._ctx.organization_id, self._project_id, record.id)
        record.storage_key = key

        provider = await storage_resolver.get_provider(self._project_id)
        upload_url = await provider.generate_presigned_upload_url(
            key, req.content_type, req.size_bytes, expires_in=3600,
        )
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await self._outbox.publish(
            f"filenest.{self._ctx.organization_id}.{self._project_id}.file.upload.initiated",
            {"file_id": record.id, "filename": req.filename, "size_bytes": req.size_bytes},
            organization_id=self._ctx.organization_id,
            project_id=self._project_id,
        )

        await self._session.commit()

        return UploadInitResponse(
            file_id=record.id, upload_url=upload_url, expires_at=expires_at,
        )

    async def confirm_upload(self, file_id: str) -> ConfirmUploadResponse:
        """
        Transition a file out of the pending state after the client PUT completes.

        Reads project_configs.virus_scan_enabled to decide the next status:
          - True  → status=processing, emits file.uploaded so ProcessingWorker
                    picks it up for virus scan / MIME validation / classification.
          - False → status=ready, emits file.ready directly (no pipeline needed).

        Both paths write the status update and the outbox event in the same
        transaction so they are atomic.
        """
        await self._repo.get(file_id, self._ctx.organization_id, self._project_id)

        config = await self._config_repo.get_for_project(
            self._project_id, self._ctx.organization_id
        )

        if config.virus_scan_enabled:
            record = await self._repo.update_status(file_id, "processing")
            await self._outbox.publish(
                f"filenest.{self._ctx.organization_id}.{self._project_id}.file.uploaded",
                {
                    "file_id": record.id,
                    "filename": record.filename,
                    "storage_key": record.storage_key,
                    "content_type": record.content_type,
                    "size_bytes": record.size_bytes,
                },
                organization_id=self._ctx.organization_id,
                project_id=self._project_id,
            )
        else:
            record = await self._repo.update_status(file_id, "ready")
            await self._outbox.publish(
                f"filenest.{self._ctx.organization_id}.{self._project_id}.file.ready",
                {
                    "file_id": record.id,
                    "filename": record.filename,
                    "storage_key": record.storage_key,
                },
                organization_id=self._ctx.organization_id,
                project_id=self._project_id,
            )

        await self._session.commit()
        return ConfirmUploadResponse(id=record.id, status=record.status)

    async def get_file(self, file_id: str) -> FileResponse:
        """Return the full metadata record for a single file."""
        record = await self._repo.get(file_id, self._ctx.organization_id, self._project_id)
        return self._to_response(record)

    async def get_download_url(self, file_id: str, *, ttl: int = 3600) -> DownloadUrlResponse:
        """Generate a presigned download URL for a file."""
        record = await self._repo.get(file_id, self._ctx.organization_id, self._project_id)

        provider = await storage_resolver.get_provider(self._project_id)
        url = await provider.generate_presigned_download_url(
            record.storage_key, filename=record.filename, expires_in=ttl,
        )
        return DownloadUrlResponse(url=url, expires_at=datetime.now(UTC) + timedelta(seconds=ttl))

    async def delete_file(self, file_id: str) -> DeleteResponse:
        """Soft-delete a file. Bytes are removed from storage via background event."""
        record = await self._repo.soft_delete(file_id, self._ctx.organization_id, self._project_id)

        await self._outbox.publish(
            f"filenest.{self._ctx.organization_id}.{self._project_id}.file.deleted",
            {"file_id": record.id, "storage_key": record.storage_key, "filename": record.filename},
            organization_id=self._ctx.organization_id,
            project_id=self._project_id,
        )

        await self._session.commit()
        return DeleteResponse(id=record.id)

    async def list_files(
        self, *, folder_id: str | None = None, limit: int = 50, cursor: str | None = None,
    ) -> FileListResponse:
        """Return a cursor-paginated list of files in the current project."""
        records = await self._repo.list(
            self._ctx.organization_id, self._project_id,
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
