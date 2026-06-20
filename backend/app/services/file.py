"""
app.services.file — Business logic for file management and file versioning.

All file business rules live here. Coordinates with FileRepository (DB),
FileVersionRepository (DB), ProjectConfigRepository (per-project feature flags),
TransactionalOutboxPublisher (events), and StorageResolver (storage backend).

confirm_upload flow (Phase 2):
  - virus_scan_enabled = true  → status=processing, emit file.uploaded
    (ProcessingWorker picks this up and runs stages)
  - virus_scan_enabled = false → status=ready, emit file.ready directly
  - versioning_enabled = true  → also creates a FileVersion row and bumps
    file.version_count (happens regardless of scan flag)

project_id always comes from the URL path parameter, not the token. The router
validates that a project-scoped token's project_id matches the URL before
constructing this service.

Usage:
    svc = FileService(session=session, repo=repo, version_repo=version_repo,
                      config_repo=config_repo, outbox=outbox, ctx=ctx,
                      project_id=project_id)
    result = await svc.init_upload(request_body)
"""
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TenantContext
from app.core.messaging import TransactionalOutboxPublisher
from app.repositories.file import FileRepository
from app.repositories.file_version import FileVersionRepository
from app.repositories.project_config import ProjectConfigRepository

from app.schemas.file import (
    ConfirmUploadResponse,
    DeleteResponse,
    DownloadUrlResponse,
    FileListResponse,
    FileResponse,
    FileVersionListResponse,
    FileVersionResponse,
    RestoreVersionResponse,
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
        session:      Active DB session (owns commit/rollback).
        repo:         FileRepository for file CRUD.
        version_repo: FileVersionRepository for version history.
        config_repo:  ProjectConfigRepository for feature flag lookups.
        outbox:       TransactionalOutboxPublisher for event enqueuing.
        ctx:          Resolved caller identity.
        project_id:   Project UUID from the URL path parameter.
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: FileRepository,
        version_repo: FileVersionRepository,
        config_repo: ProjectConfigRepository,
        outbox: TransactionalOutboxPublisher,
        ctx: TenantContext,
        project_id: str,
    ) -> None:
        self._session = session
        self._ctx = ctx
        self._project_id = project_id
        self._repo = repo
        self._version_repo = version_repo
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

        Reads project_configs flags to decide behaviour:
          virus_scan_enabled = True  → status=processing, emits file.uploaded so
                                       ProcessingWorker runs virus scan / MIME validation.
          virus_scan_enabled = False → status=ready, emits file.ready directly.
          versioning_enabled = True  → creates a FileVersion snapshot and bumps
                                       file.version_count (always, regardless of scan flag).

        All writes happen in the same transaction.
        """
        record = await self._repo.get(file_id, self._ctx.organization_id, self._project_id)

        config = await self._config_repo.get_for_project(
            self._project_id, self._ctx.organization_id
        )

        if config.versioning_enabled and record.storage_key:
            record.version_count = (record.version_count or 0) + 1
            await self._version_repo.create(
                file_id=record.id,
                organization_id=self._ctx.organization_id,
                project_id=self._project_id,
                version_number=record.version_count,
                storage_key=record.storage_key,
                size_bytes=record.size_bytes,
                content_type=record.content_type,
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

    async def list_versions(self, file_id: str) -> FileVersionListResponse:
        """
        List all version snapshots for a file, newest first.

        Returns an empty list when versioning was never enabled for this file.
        """
        await self._repo.get(file_id, self._ctx.organization_id, self._project_id)
        versions = await self._version_repo.list(
            file_id, self._ctx.organization_id, self._project_id
        )
        items = [self._to_version_response(v) for v in versions]
        return FileVersionListResponse(items=items, total=len(items))

    async def get_version_download_url(
        self, file_id: str, version_id: str, *, ttl: int = 3600
    ) -> DownloadUrlResponse:
        """
        Generate a presigned download URL for a specific version's bytes.

        The version's own storage_key is used so the URL points to the
        exact bytes from when that version was created.
        """
        await self._repo.get(file_id, self._ctx.organization_id, self._project_id)
        version = await self._version_repo.get(
            version_id, file_id, self._ctx.organization_id
        )
        provider = await storage_resolver.get_provider(self._project_id)
        url = await provider.generate_presigned_download_url(
            version.storage_key, expires_in=ttl
        )
        return DownloadUrlResponse(
            url=url, expires_at=datetime.now(UTC) + timedelta(seconds=ttl)
        )

    async def restore_version(self, file_id: str, version_id: str) -> RestoreVersionResponse:
        """
        Restore a past version as the current file state.

        Updates the file record's storage_key, size_bytes, and content_type to
        match the chosen version, then creates a new FileVersion row so the
        restore itself is captured in the history. Emits file.restored.

        Returns:
            RestoreVersionResponse with the new version_number after restore.
        """
        record = await self._repo.get(file_id, self._ctx.organization_id, self._project_id)
        version = await self._version_repo.get(
            version_id, file_id, self._ctx.organization_id
        )

        now = datetime.now(UTC)
        record.storage_key = version.storage_key
        record.size_bytes = version.size_bytes
        record.content_type = version.content_type
        record.status = "ready"
        record.updated_at = now
        record.version_count = (record.version_count or 0) + 1

        await self._version_repo.create(
            file_id=record.id,
            organization_id=self._ctx.organization_id,
            project_id=self._project_id,
            version_number=record.version_count,
            storage_key=version.storage_key,
            size_bytes=version.size_bytes,
            content_type=version.content_type,
        )

        await self._outbox.publish(
            f"filenest.{self._ctx.organization_id}.{self._project_id}.file.restored",
            {
                "file_id": record.id,
                "restored_from_version": version.version_number,
                "new_version_number": record.version_count,
                "storage_key": version.storage_key,
            },
            organization_id=self._ctx.organization_id,
            project_id=self._project_id,
        )

        await self._session.commit()
        return RestoreVersionResponse(
            file_id=record.id, version_number=record.version_count
        )

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

    def _to_version_response(self, version) -> FileVersionResponse:
        return FileVersionResponse(
            id=version.id,
            file_id=version.file_id,
            version_number=version.version_number,
            storage_key=version.storage_key,
            size_bytes=version.size_bytes,
            content_type=version.content_type,
            created_at=version.created_at,
        )
