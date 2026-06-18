"""
shared.auth.middleware — HTTP authentication middleware for FastAPI routes.

`authenticate_request` is the single entry point for verifying incoming API
requests. It inspects the `Authorization: Bearer <token>` header, delegates
to the appropriate verifier (JWT or API key), and stores the resolved
TenantContext in a ContextVar for the rest of the request lifecycle.

Token dispatch rules:
  - `fn_live_*` / `fn_test_*`  → API key path (IAM verify-api-key endpoint)
  - anything else               → JWT path (local HS256 decode, no network)

This function is used as a FastAPI dependency — attach it with
`Depends(authenticate_request)` on any route that requires auth, or add it
to the router-level dependencies list to protect an entire prefix.

Usage:
    from shared.auth import authenticate_request, TenantContext
    from fastapi import Depends

    @router.get("/files")
    async def list_files(ctx: TenantContext = Depends(authenticate_request)):
        ...
"""
from fastapi import Depends, HTTPException, Request, status

from shared.auth.tenant import TenantContext, set_tenant_context
from shared.auth.token import verify_api_key, verify_jwt


async def authenticate_request(
    request: Request,
) -> TenantContext:
    """
    Resolve a TenantContext from the request's Authorization header.

    Reads the Bearer token, dispatches to the correct verifier, stores the
    result in the async ContextVar, and returns the context so FastAPI can
    inject it into route handlers.

    Raises:
        HTTPException 401: If the Authorization header is missing or malformed.
        HTTPException 401: If the token is invalid, expired, revoked, or unknown.
        HTTPException 503: If the IAM cannot be reached when verifying an API key.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_CREDENTIALS"},
        )

    token = auth_header.removeprefix("Bearer ")

    if token.startswith(("fn_live_", "fn_test_")):
        ctx = await verify_api_key(token)
    else:
        ctx = await verify_jwt(token)

    set_tenant_context(ctx)
    return ctx
