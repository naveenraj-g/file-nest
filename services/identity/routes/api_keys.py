"""
services.identity.routes.api_keys — HTTP handlers for API key management.

Routes are thin: validate input via Pydantic schemas, call ApiKeyService,
return a typed response. No SQL, no hashing logic here.

All routes require authentication (enforced by get_identity_service) and the
`api_keys:create` / `api_keys:revoke` scopes.

Final paths (registered at /v1 prefix in router.py):
    POST   /v1/api-keys              create a new API key
    GET    /v1/api-keys              list API keys for the current project
    DELETE /v1/api-keys/{key_id}     revoke an API key
"""
from fastapi import APIRouter, Depends

from shared.auth import require_scope

from ..dependencies import get_identity_service
from ..schemas import ApiKeyListResponse, ApiKeyResponse, CreateApiKeyRequest
from ..service import ApiKeyService

router = APIRouter(tags=["API Keys"])


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    svc: ApiKeyService = Depends(get_identity_service),
) -> ApiKeyResponse:
    """
    Create a new API key for the current project.

    The raw key value is returned exactly once in the `key` field. Store it
    immediately — it cannot be retrieved again. Required scope: `api_keys:create`.
    """
    require_scope("api_keys:create")
    return await svc.create_api_key(body)


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    svc: ApiKeyService = Depends(get_identity_service),
) -> ApiKeyListResponse:
    """
    List all API keys for the current project (including revoked).

    The `key` field is always null in list responses. Required scope: `api_keys:create`.
    """
    require_scope("api_keys:create")
    return await svc.list_api_keys()


@router.delete("/api-keys/{key_id}", response_model=ApiKeyResponse)
async def revoke_api_key(
    key_id: str,
    svc: ApiKeyService = Depends(get_identity_service),
) -> ApiKeyResponse:
    """
    Revoke an API key. The key is immediately rejected on future requests.

    Returns the updated key record with `is_revoked=true`. Required scope: `api_keys:revoke`.
    """
    require_scope("api_keys:revoke")
    return await svc.revoke_api_key(key_id)
