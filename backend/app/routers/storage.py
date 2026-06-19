"""
app.routers.storage — HTTP handlers for storage configuration.

Routes registered at /v1 prefix:
    PATCH /v1/projects/{project_id}/storage         save BYOB credentials (encrypted)
    GET   /v1/projects/{project_id}/storage         current storage config (no credentials)
    POST  /v1/projects/{project_id}/storage/verify  connectivity probe (write + delete)
"""
from fastapi import APIRouter, Depends

from app.auth import require_scope
from app.di.dependencies.storage_config import get_storage_config_service
from app.schemas.storage_config import StorageConfigResponse, StorageConfigUpdateRequest, StorageVerifyResponse
from app.services.storage_config import StorageConfigService

router = APIRouter(tags=["Storage"])


@router.patch("/projects/{project_id}/storage", response_model=StorageConfigResponse)
async def update_storage_config(
    project_id: str,
    body: StorageConfigUpdateRequest,
    svc: StorageConfigService = Depends(get_storage_config_service),
) -> StorageConfigResponse:
    """
    Save BYOB credentials for a project's storage config.

    After saving, status is set to pending_verification. Call the
    /verify endpoint to run a connectivity probe and activate it.
    Scope: projects:update.
    """
    require_scope(svc._ctx, "projects:update")
    return await svc.update_config(project_id, body)


@router.get("/projects/{project_id}/storage", response_model=StorageConfigResponse)
async def get_storage_config(
    project_id: str,
    svc: StorageConfigService = Depends(get_storage_config_service),
) -> StorageConfigResponse:
    """Return the non-sensitive storage config for a project. Scope: projects:read."""
    require_scope(svc._ctx, "projects:read")
    return await svc.get_config(project_id)


@router.post("/projects/{project_id}/storage/verify", response_model=StorageVerifyResponse)
async def verify_storage(
    project_id: str,
    svc: StorageConfigService = Depends(get_storage_config_service),
) -> StorageVerifyResponse:
    """
    Probe the project's storage provider (write + delete a test object).
    Updates config status to active on success, verification_failed on error.
    Scope: projects:update.
    """
    require_scope(svc._ctx, "projects:update")
    return await svc.verify(project_id)
