"""
app.routers.files — HTTP handlers for file management.

Routes registered at /v1 prefix:
    POST   /v1/files/upload              initiate an upload (get presigned PUT URL)
    POST   /v1/files/{file_id}/confirm   confirm upload completed
    GET    /v1/files/{file_id}           fetch file metadata
    GET    /v1/files/{file_id}/download  get presigned download URL
    GET    /v1/files                     list files (cursor-paginated)
    DELETE /v1/files/{file_id}           soft-delete a file
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TenantContext, authenticate_request, require_scope
from app.core.database import get_db
from app.schemas.file import (
    ConfirmUploadResponse,
    DeleteResponse,
    DownloadUrlResponse,
    FileListResponse,
    FileResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from app.services.file import FileService

router = APIRouter(tags=["Files"])


def _get_service(
    session: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(authenticate_request),
) -> FileService:
    return FileService(session=session, ctx=ctx)


@router.post("/files/upload", response_model=UploadInitResponse, status_code=201)
async def init_upload(
    body: UploadInitRequest,
    svc: FileService = Depends(_get_service),
) -> UploadInitResponse:
    """Initiate a single-file upload and return a presigned PUT URL. Scope: files:upload."""
    require_scope(svc._ctx, "files:upload")
    return await svc.init_upload(body)


@router.post("/files/{file_id}/confirm", response_model=ConfirmUploadResponse)
async def confirm_upload(
    file_id: str,
    svc: FileService = Depends(_get_service),
) -> ConfirmUploadResponse:
    """Confirm that bytes have been PUT to storage. Transitions status to ready. Scope: files:upload."""
    require_scope(svc._ctx, "files:upload")
    return await svc.confirm_upload(file_id)


@router.get("/files/{file_id}/download", response_model=DownloadUrlResponse)
async def get_download_url(
    file_id: str,
    ttl: int = Query(3600, ge=60, le=86400, description="URL TTL in seconds"),
    svc: FileService = Depends(_get_service),
) -> DownloadUrlResponse:
    """Generate a presigned download URL. Scope: files:download."""
    require_scope(svc._ctx, "files:download")
    return await svc.get_download_url(file_id, ttl=ttl)


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    svc: FileService = Depends(_get_service),
) -> FileResponse:
    """Fetch file metadata. Scope: files:read."""
    require_scope(svc._ctx, "files:read")
    return await svc.get_file(file_id)


@router.get("/files", response_model=FileListResponse)
async def list_files(
    folder_id: str | None = Query(None, description="Filter to files in this folder"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    cursor: str | None = Query(None, description="Last file id from previous page"),
    svc: FileService = Depends(_get_service),
) -> FileListResponse:
    """Return a cursor-paginated list of files in the current project. Scope: files:read."""
    require_scope(svc._ctx, "files:read")
    return await svc.list_files(folder_id=folder_id, limit=limit, cursor=cursor)


@router.delete("/files/{file_id}", response_model=DeleteResponse)
async def delete_file(
    file_id: str,
    svc: FileService = Depends(_get_service),
) -> DeleteResponse:
    """Soft-delete a file. Scope: files:delete."""
    require_scope(svc._ctx, "files:delete")
    return await svc.delete_file(file_id)
