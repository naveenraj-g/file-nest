"""
shared.auth — Public API for authentication and authorisation.

Re-exports the three things most service code will import:
  - TenantContext     — the resolved caller identity (org, project, scopes)
  - authenticate_request — FastAPI dependency that validates the Bearer token
  - require_scope     — asserts a scope is present, raises 403 if not
  - get_tenant_context / require_auth — read the ContextVar directly

Usage:
    from shared.auth import authenticate_request, require_scope, TenantContext
    from fastapi import Depends

    @router.get("/files")
    async def list_files(ctx: TenantContext = Depends(authenticate_request)):
        require_scope("files:read")
        ...
"""
from .middleware import authenticate_request
from .permissions import require_scope
from .tenant import TenantContext, get_tenant_context, require_auth

__all__ = [
    "TenantContext",
    "require_auth",
    "get_tenant_context",
    "require_scope",
    "authenticate_request",
]
