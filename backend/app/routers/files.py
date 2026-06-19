"""
app.routers.files — HTTP handlers for file management.

Routes are project-scoped: project_id comes from the URL path so that both
org-level and project-level tokens work. A project-scoped token's project_id
must match the URL; an org-level token may operate on any project in the org.

Routes registered at /v1 prefix:
    POST   /v1/projects/{project_id}/files/upload              initiate upload (presigned PUT URL)
    POST   /v1/projects/{project_id}/files/{file_id}/confirm   confirm upload completed
    GET    /v1/projects/{project_id}/files/{file_id}           fetch file metadata
    GET    /v1/projects/{project_id}/files/{file_id}/download  get presigned download URL
    GET    /v1/projects/{project_id}/files                     list files (cursor-paginated)
    DELETE /v1/projects/{project_id}/files/{file_id}           soft-delete a file
"""
from fastapi import APIRouter, Depends, Query

from app.auth import require_scope
from app.di.dependencies.file import get_file_service
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


@router.post("/projects/{project_id}/files/upload", response_model=UploadInitResponse, status_code=201)
async def init_upload(
    project_id: str,
    body: UploadInitRequest,
    svc: FileService = Depends(get_file_service),
) -> UploadInitResponse:
    """Initiate a single-file upload and return a presigned PUT URL. Scope: files:upload."""
    require_scope(svc._ctx, "files:upload")
    return await svc.init_upload(body)


@router.post("/projects/{project_id}/files/{file_id}/confirm", response_model=ConfirmUploadResponse)
async def confirm_upload(
    project_id: str,
    file_id: str,
    svc: FileService = Depends(get_file_service),
) -> ConfirmUploadResponse:
    """Confirm bytes have been PUT to storage. Transitions status → ready. Scope: files:upload."""
    require_scope(svc._ctx, "files:upload")
    return await svc.confirm_upload(file_id)


@router.get("/projects/{project_id}/files/{file_id}/download", response_model=DownloadUrlResponse)
async def get_download_url(
    project_id: str,
    file_id: str,
    ttl: int = Query(3600, ge=60, le=86400, description="URL TTL in seconds"),
    svc: FileService = Depends(get_file_service),
) -> DownloadUrlResponse:
    """Generate a presigned download URL. Scope: files:download."""
    require_scope(svc._ctx, "files:download")
    return await svc.get_download_url(file_id, ttl=ttl)


@router.get("/projects/{project_id}/files/{file_id}", response_model=FileResponse)
async def get_file(
    project_id: str,
    file_id: str,
    svc: FileService = Depends(get_file_service),
) -> FileResponse:
    """Fetch file metadata. Scope: files:read."""
    require_scope(svc._ctx, "files:read")
    return await svc.get_file(file_id)


@router.get("/projects/{project_id}/files", response_model=FileListResponse)
async def list_files(
    project_id: str,
    folder_id: str | None = Query(None, description="Filter to files in this folder"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    cursor: str | None = Query(None, description="Last file id from previous page"),
    svc: FileService = Depends(get_file_service),
) -> FileListResponse:
    """Return a cursor-paginated list of files in the project. Scope: files:read."""
    require_scope(svc._ctx, "files:read")
    return await svc.list_files(folder_id=folder_id, limit=limit, cursor=cursor)


@router.delete("/projects/{project_id}/files/{file_id}", response_model=DeleteResponse)
async def delete_file(
    project_id: str,
    file_id: str,
    svc: FileService = Depends(get_file_service),
) -> DeleteResponse:
    """Soft-delete a file. Scope: files:delete."""
    require_scope(svc._ctx, "files:delete")
    return await svc.delete_file(file_id)
