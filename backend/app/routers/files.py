"""
app.routers.files — HTTP handlers for file management and file versioning.

Routes are project-scoped: project_id comes from the URL path so that both
org-level and project-level tokens work. A project-scoped token's project_id
must match the URL; an org-level token may operate on any project in the org.

Routes registered at /v1 prefix:
    POST   /v1/projects/{project_id}/files/upload                                  initiate upload
    POST   /v1/projects/{project_id}/files/{file_id}/confirm                       confirm upload
    GET    /v1/projects/{project_id}/files/{file_id}                               file metadata
    GET    /v1/projects/{project_id}/files/{file_id}/download                      presigned download URL
    GET    /v1/projects/{project_id}/files                                         list files
    DELETE /v1/projects/{project_id}/files/{file_id}                               soft-delete
    GET    /v1/projects/{project_id}/files/{file_id}/versions                      list versions
    GET    /v1/projects/{project_id}/files/{file_id}/versions/{version_id}/download version download URL
    POST   /v1/projects/{project_id}/files/{file_id}/versions/{version_id}/restore restore version
"""
from fastapi import APIRouter, Depends, Query

from app.auth import require_scope
from app.di.dependencies.file import get_file_service
from app.di.dependencies.multipart import get_multipart_service
from app.schemas.file import (
    ConfirmUploadResponse,
    DeleteResponse,
    DownloadUrlResponse,
    FileListResponse,
    FileResponse,
    FileVersionListResponse,
    MultipartAbortResponse,
    MultipartCompleteRequest,
    MultipartCompleteResponse,
    MultipartPartUrlResponse,
    MultipartStartRequest,
    MultipartStartResponse,
    RestoreVersionResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from app.services.file import FileService
from app.services.multipart import MultipartUploadService

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
    return await svc.get_download_url(file_id, caller_ttl=ttl)


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


@router.get(
    "/projects/{project_id}/files/{file_id}/versions",
    response_model=FileVersionListResponse,
)
async def list_versions(
    project_id: str,
    file_id: str,
    svc: FileService = Depends(get_file_service),
) -> FileVersionListResponse:
    """List all version snapshots for a file, newest first. Scope: files:read."""
    require_scope(svc._ctx, "files:read")
    return await svc.list_versions(file_id)


@router.get(
    "/projects/{project_id}/files/{file_id}/versions/{version_id}/download",
    response_model=DownloadUrlResponse,
)
async def get_version_download_url(
    project_id: str,
    file_id: str,
    version_id: str,
    ttl: int = Query(3600, ge=60, le=86400, description="URL TTL in seconds"),
    svc: FileService = Depends(get_file_service),
) -> DownloadUrlResponse:
    """Generate a presigned download URL for a specific version's bytes. Scope: files:download."""
    require_scope(svc._ctx, "files:download")
    return await svc.get_version_download_url(file_id, version_id, caller_ttl=ttl)


@router.post(
    "/projects/{project_id}/files/{file_id}/versions/{version_id}/restore",
    response_model=RestoreVersionResponse,
)
async def restore_version(
    project_id: str,
    file_id: str,
    version_id: str,
    svc: FileService = Depends(get_file_service),
) -> RestoreVersionResponse:
    """Restore a past version as the current file state. Scope: files:update_metadata."""
    require_scope(svc._ctx, "files:update_metadata")
    return await svc.restore_version(file_id, version_id)


# ── Multipart upload ────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/files/upload/multipart/start",
    response_model=MultipartStartResponse,
    status_code=201,
)
async def multipart_start(
    project_id: str,
    body: MultipartStartRequest,
    svc: MultipartUploadService = Depends(get_multipart_service),
) -> MultipartStartResponse:
    """Initiate a multipart upload. Validates file size against project limit. Scope: files:upload."""
    require_scope(svc._ctx, "files:upload")
    return await svc.start(body)


@router.get(
    "/projects/{project_id}/files/upload/multipart/{upload_id}/part-url",
    response_model=MultipartPartUrlResponse,
)
async def multipart_part_url(
    project_id: str,
    upload_id: str,
    part: int = Query(..., ge=1, le=10000, description="1-based part number"),
    ttl: int = Query(3600, ge=60, le=86400, description="Presigned URL TTL in seconds"),
    svc: MultipartUploadService = Depends(get_multipart_service),
) -> MultipartPartUrlResponse:
    """Generate a presigned URL for uploading a single part. Scope: files:upload."""
    require_scope(svc._ctx, "files:upload")
    return await svc.part_url(upload_id, part, caller_ttl=ttl)


@router.post(
    "/projects/{project_id}/files/upload/multipart/{upload_id}/complete",
    response_model=MultipartCompleteResponse,
)
async def multipart_complete(
    project_id: str,
    upload_id: str,
    body: MultipartCompleteRequest,
    svc: MultipartUploadService = Depends(get_multipart_service),
) -> MultipartCompleteResponse:
    """Assemble all uploaded parts into the final object. Scope: files:upload."""
    require_scope(svc._ctx, "files:upload")
    return await svc.complete(upload_id, body)


@router.delete(
    "/projects/{project_id}/files/upload/multipart/{upload_id}",
    response_model=MultipartAbortResponse,
)
async def multipart_abort(
    project_id: str,
    upload_id: str,
    svc: MultipartUploadService = Depends(get_multipart_service),
) -> MultipartAbortResponse:
    """Abort an in-progress multipart upload and discard all parts. Scope: files:upload."""
    require_scope(svc._ctx, "files:upload")
    return await svc.abort(upload_id)
