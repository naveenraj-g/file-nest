"""
app.services.folder — Business logic for folder management.

Handles folder creation (with path materialisation), listing, file listing
inside a folder, and safe deletion (rejects if folder is non-empty).

Path materialisation:
  - Root-level folder (no parent): path = "/{name}"
  - Child folder: path = "{parent.path}/{name}"
  Paths are built once at creation and never recomputed, making breadcrumb
  display O(1) — just split the path string.

Usage:
    svc = FolderService(session=session, repo=repo, file_repo=file_repo, ctx=ctx, project_id=project_id)
    result = await svc.create_folder(req)
"""
import asyncio
import json
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TenantContext
from app.errors import ConflictError
from app.models.folder import Folder
from app.repositories.file import FileRepository
from app.repositories.folder import FolderRepository
from app.schemas.file import FileListResponse
from app.schemas.folder import (
    DeleteFolderResponse,
    FolderCreateRequest,
    FolderListResponse,
    FolderResponse,
)


class FolderService:
    """
    Orchestrates folder operations for a single request.

    Args:
        session:    Active DB session (owns commit/rollback).
        repo:       FolderRepository for folder CRUD.
        file_repo:  FileRepository for listing files inside a folder.
        ctx:        Resolved caller identity.
        project_id: Project UUID from the URL path parameter.
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: FolderRepository,
        file_repo: FileRepository,
        ctx: TenantContext,
        project_id: str,
    ) -> None:
        self._session = session
        self._ctx = ctx
        self._project_id = project_id
        self._repo = repo
        self._file_repo = file_repo

    async def create_folder(self, req: FolderCreateRequest) -> FolderResponse:
        """
        Create a new folder, materialising its full path at creation time.

        If parent_folder_id is provided, the parent must exist and belong to the
        same project. The new folder's path is "{parent.path}/{name}".
        Root-level folders get path "/{name}".

        Raises:
            NotFoundError: If parent_folder_id is provided but does not exist.
        """
        if req.parent_folder_id is not None:
            parent = await self._repo.get(
                req.parent_folder_id, self._ctx.organization_id, self._project_id
            )
            path = f"{parent.path}/{req.name}"
        else:
            path = f"/{req.name}"

        record = await self._repo.create(
            organization_id=self._ctx.organization_id,
            project_id=self._project_id,
            name=req.name,
            path=path,
            parent_folder_id=req.parent_folder_id,
        )
        await self._session.commit()
        return self._to_response(record)

    async def list_folders(self) -> FolderListResponse:
        """Return all active folders in the project, ordered by path."""
        records = await self._repo.list(self._ctx.organization_id, self._project_id)
        items = [self._to_response(r) for r in records]
        return FolderListResponse(items=items, total=len(items))

    async def list_folder_files(
        self,
        folder_id: str,
        *,
        q: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
        cursor: str | None = None,
    ) -> FileListResponse:
        """
        List files inside a specific folder with the same filter + pagination set as the global file list.

        Verifies the folder exists and belongs to this project before querying.

        Raises:
            NotFoundError: If the folder does not exist.
        """
        await self._repo.get(folder_id, self._ctx.organization_id, self._project_id)

        filter_kwargs: dict[str, Any] = dict(
            folder_id=folder_id, q=q, tags=tags, category=category,
            status=status, date_from=date_from, date_to=date_to,
            size_min=size_min, size_max=size_max, metadata_filter=metadata_filter,
        )
        total, records = await asyncio.gather(
            self._file_repo.count(self._ctx.organization_id, self._project_id, **filter_kwargs),
            self._file_repo.list(
                self._ctx.organization_id, self._project_id,
                **filter_kwargs, limit=limit, offset=offset, cursor=cursor,
            ),
        )

        from app.schemas.file import FileResponse
        items = [
            FileResponse(
                id=r.id,
                organization_id=r.organization_id,
                project_id=r.project_id,
                filename=r.filename,
                content_type=r.content_type,
                size_bytes=r.size_bytes,
                status=r.status,
                storage_key=r.storage_key or "",
                folder_id=r.folder_id,
                category=r.category,
                version_count=r.version_count or 0,
                tags=r.tags or [],
                metadata=json.loads(r.metadata_json or "{}"),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ]
        has_more = len(items) == limit and (offset + limit) < total if not cursor else len(items) == limit
        return FileListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset if not cursor else 0,
            has_more=has_more,
            next_cursor=items[-1].id if items and has_more else None,
        )

    async def delete_folder(self, folder_id: str) -> DeleteFolderResponse:
        """
        Soft-delete a folder.

        Rejects with ConflictError if the folder still contains active files
        or active subfolders — callers must empty the folder first.

        Raises:
            NotFoundError:  If the folder does not exist.
            ConflictError:  If the folder is non-empty.
        """
        if await self._repo.has_subfolders(
            folder_id, self._ctx.organization_id, self._project_id
        ):
            raise ConflictError(
                "Folder cannot be deleted while it contains subfolders",
                detail={"folder_id": folder_id, "reason": "has_subfolders"},
            )
        if await self._repo.has_files(
            folder_id, self._ctx.organization_id, self._project_id
        ):
            raise ConflictError(
                "Folder cannot be deleted while it contains files",
                detail={"folder_id": folder_id, "reason": "has_files"},
            )
        await self._repo.soft_delete(
            folder_id, self._ctx.organization_id, self._project_id
        )
        await self._session.commit()
        return DeleteFolderResponse(id=folder_id)

    def _to_response(self, record: Folder) -> FolderResponse:
        return FolderResponse(
            id=record.id,
            organization_id=record.organization_id,
            project_id=record.project_id,
            parent_folder_id=record.parent_folder_id,
            name=record.name,
            path=record.path,
            created_at=record.created_at,
        )
