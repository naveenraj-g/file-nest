"""
app.routers.folders — HTTP handlers for folder management and file move.

All routes are project-scoped. project_id comes from the URL path.

Routes registered at /v1 prefix:
    POST   /v1/projects/{project_id}/folders                            create folder
    GET    /v1/projects/{project_id}/folders                            list folders
    GET    /v1/projects/{project_id}/folders/{folder_id}/files          list files in folder
    DELETE /v1/projects/{project_id}/folders/{folder_id}                soft-delete folder
    POST   /v1/projects/{project_id}/files/{file_id}/move               move file to folder
"""
from fastapi import APIRouter, Depends, Query

from app.auth import require_scope
from app.di.dependencies.file import get_file_service
from app.di.dependencies.folder import get_folder_service
from app.schemas.file import FileListResponse, MoveFileRequest, FileResponse
from app.schemas.folder import (
    DeleteFolderResponse,
    FolderCreateRequest,
    FolderListResponse,
    FolderResponse,
)
from app.services.file import FileService
from app.services.folder import FolderService

router = APIRouter(tags=["Folders"])


@router.post(
    "/projects/{project_id}/folders",
    response_model=FolderResponse,
    status_code=201,
)
async def create_folder(
    project_id: str,
    body: FolderCreateRequest,
    svc: FolderService = Depends(get_folder_service),
) -> FolderResponse:
    """Create a new folder (optionally nested). Scope: files:update_metadata."""
    require_scope(svc._ctx, "files:update_metadata")
    return await svc.create_folder(body)


@router.get("/projects/{project_id}/folders", response_model=FolderListResponse)
async def list_folders(
    project_id: str,
    svc: FolderService = Depends(get_folder_service),
) -> FolderListResponse:
    """List all folders in the project, ordered by path. Scope: files:read."""
    require_scope(svc._ctx, "files:read")
    return await svc.list_folders()


@router.get(
    "/projects/{project_id}/folders/{folder_id}/files",
    response_model=FileListResponse,
)
async def list_folder_files(
    project_id: str,
    folder_id: str,
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    cursor: str | None = Query(None, description="Last file id from previous page"),
    svc: FolderService = Depends(get_folder_service),
) -> FileListResponse:
    """Return files inside a specific folder, cursor-paginated. Scope: files:read."""
    require_scope(svc._ctx, "files:read")
    return await svc.list_folder_files(folder_id, limit=limit, cursor=cursor)


@router.delete(
    "/projects/{project_id}/folders/{folder_id}",
    response_model=DeleteFolderResponse,
)
async def delete_folder(
    project_id: str,
    folder_id: str,
    svc: FolderService = Depends(get_folder_service),
) -> DeleteFolderResponse:
    """Soft-delete a folder. Fails with 409 if it contains files or subfolders. Scope: files:update_metadata."""
    require_scope(svc._ctx, "files:update_metadata")
    return await svc.delete_folder(folder_id)


@router.post(
    "/projects/{project_id}/files/{file_id}/move",
    response_model=FileResponse,
)
async def move_file(
    project_id: str,
    file_id: str,
    body: MoveFileRequest,
    svc: FileService = Depends(get_file_service),
) -> FileResponse:
    """Move a file to a different folder, or to the root when folder_id is null. Scope: files:update_metadata."""
    require_scope(svc._ctx, "files:update_metadata")
    return await svc.move_file(file_id, body)
