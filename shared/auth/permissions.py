"""
shared.auth.permissions — Scope-based access control for FastAPI routes.

`require_scope` reads the current TenantContext from the ContextVar (set by
`authenticate_request`) and raises HTTP 403 if the caller's token does not
include all of the requested scopes.

Use it as a synchronous call inside route handlers after authentication, or
wrap it in a FastAPI dependency for per-route enforcement.

Available scopes (as of Phase 1):
    files:upload            files:download          files:read
    files:delete            files:update_metadata
    api_keys:create         api_keys:revoke
    projects:read           projects:update
    audit:read              compliance:manage

Usage:
    from shared.auth.permissions import require_scope

    @router.post("/files/upload")
    async def upload(ctx: TenantContext = Depends(authenticate_request)):
        require_scope("files:upload")   # raises 403 if scope is absent
        ...
"""
from fastapi import HTTPException, status

from shared.auth.tenant import get_tenant_context


def require_scope(*scopes: str) -> None:
    """
    Assert that the current request's token includes all of the given scopes.

    Args:
        *scopes: One or more scope strings that must all be present.

    Raises:
        HTTPException 403: If any scope is missing, with a list of the missing ones.
    """
    ctx = get_tenant_context()
    missing = [s for s in scopes if s not in ctx.scopes]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERMISSION_DENIED", "missing_scopes": missing},
        )
