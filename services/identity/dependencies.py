"""
services.identity.dependencies — FastAPI dependency wiring for the Identity Service.

Defines `get_identity_service` which constructs an ApiKeyService for each request,
injecting the database session and the resolved TenantContext from the auth
middleware. Route handlers never construct ApiKeyService directly.

Usage:
    from services.identity.dependencies import get_identity_service
    from services.identity.service import ApiKeyService
    from fastapi import Depends

    @router.post("/api-keys")
    async def create_key(svc: ApiKeyService = Depends(get_identity_service)):
        ...
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import TenantContext, authenticate_request
from shared.database import get_db

from .service import ApiKeyService


async def get_identity_service(
    session: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(authenticate_request),
) -> ApiKeyService:
    """
    Construct an ApiKeyService bound to the current request's session and tenant.

    FastAPI resolves `get_db` and `authenticate_request` first, then passes
    both into this function. The resulting service is scoped to one request.
    """
    return ApiKeyService(session=session, ctx=ctx)
