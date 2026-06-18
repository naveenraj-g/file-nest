"""
services.file.router — HTTP route definitions for the File Service.

Routes are intentionally thin: validate input via Pydantic schemas, call
FileService, return a typed response. No SQL, no storage calls here.

All routes require authentication (enforced by `get_file_service`). Scope checks
are performed inside each handler via `require_scope()`.

Registered at prefix /v1 in main.py — final paths:
    POST   /v1/files/upload              initiate an upload
    POST   /v1/files/{file_id}/confirm   confirm upload completed
    GET    /v1/files/{file_id}           fetch file metadata
    GET    /v1/files/{file_id}/download  get presigned download URL
    GET    /v1/files                     list files (cursor-paginated)
    DELETE /v1/files/{file_id}           soft-delete a file
"""
from fastapi import APIRouter, Depends, Query

from shared.auth import require_scope

from .dependencies import get_file_service
from .schemas import (
    ConfirmUploadResponse,
    DeleteResponse,
    DownloadUrlResponse,
    FileListResponse,
    FileResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from .service import FileService

router = APIRouter(tags=["Files"])


@router.post("/files/upload", response_model=UploadInitResponse, status_code=201)
async def init_upload(
    body: UploadInitRequest,
    svc: FileService = Depends(get_file_service),
) -> UploadInitResponse:
    """
    Initiate a single-file upload and return a presigned PUT URL.

    PUT the file bytes directly to `upload_url`. Then call `/confirm` once
    the PUT completes. Required scope: `files:upload`.
    """
    require_scope("files:upload")
    return await svc.init_upload(body)


@router.post("/files/{file_id}/confirm", response_model=ConfirmUploadResponse)
async def confirm_upload(
    file_id: str,
    svc: FileService = Depends(get_file_service),
) -> ConfirmUploadResponse:
    """
    Confirm that the client has completed the PUT to storage.

    Transitions the file status from `pending` to `ready`.
    Required scope: `files:upload`.
    """
    require_scope("files:upload")
    return await svc.confirm_upload(file_id)


@router.get("/files/{file_id}/download", response_model=DownloadUrlResponse)
async def get_download_url(
    file_id: str,
    ttl: int = Query(3600, ge=60, le=86400, description="URL TTL in seconds"),
    svc: FileService = Depends(get_file_service),
) -> DownloadUrlResponse:
    """
    Generate a presigned URL to download the file bytes directly from storage.

    The URL is valid for `ttl` seconds (default 1 hour, max 24 hours).
    Required scope: `files:download`.
    """
    require_scope("files:download")
    return await svc.get_download_url(file_id, ttl=ttl)


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    svc: FileService = Depends(get_file_service),
) -> FileResponse:
    """
    Fetch the full metadata record for a single file.

    Returns 404 if the file does not exist within the caller's project scope.
    Required scope: `files:read`.
    """
    require_scope("files:read")
    return await svc.get_file(file_id)


@router.get("/files", response_model=FileListResponse)
async def list_files(
    folder_id: str | None = Query(None, description="Filter to files in this folder"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    cursor: str | None = Query(None, description="Last file id from previous page"),
    svc: FileService = Depends(get_file_service),
) -> FileListResponse:
    """
    Return a cursor-paginated list of files in the current project.

    Pass `cursor` from the previous response's `cursor` field to fetch the
    next page. A null cursor means you've reached the last page.
    Required scope: `files:read`.
    """
    require_scope("files:read")
    return await svc.list_files(folder_id=folder_id, limit=limit, cursor=cursor)


@router.delete("/files/{file_id}", response_model=DeleteResponse)
async def delete_file(
    file_id: str,
    svc: FileService = Depends(get_file_service),
) -> DeleteResponse:
    """
    Soft-delete a file. Bytes are removed from storage asynchronously.

    Returns 404 if the file does not exist. Returns 409 if a WORM or legal-hold
    policy prevents deletion (Phase 8). Required scope: `files:delete`.
    """
    require_scope("files:delete")
    return await svc.delete_file(file_id)
