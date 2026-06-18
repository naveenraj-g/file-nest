"""
app.auth.dependencies — FastAPI auth dependencies.

Provides:
  - authenticate_request  — resolves a TenantContext from the Bearer token
  - require_scope         — asserts a scope is present on the current context

Token dispatch:
  - fn_live_* / fn_test_* → POST {IAM_URL}/api/internal/verify-api-key (httpx)
  - JWT (anything else)   → JWKS verification via PyJWT + IAM's /api/auth/jwks

Usage:
    from app.auth.dependencies import authenticate_request, require_scope
    from app.auth.models import TenantContext
    from fastapi import Depends

    @router.get("/files")
    async def list_files(ctx: TenantContext = Depends(authenticate_request)):
        require_scope(ctx, "files:read")
        ...
"""
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request, status

from app.auth.models import TenantContext, set_tenant_context
from app.core.config import settings

# Module-level singleton — caches JWKS response across requests, re-fetches on key rotation.
# Lazy-initialised on first use so import-time doesn't require the IAM to be running.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.iam_jwks_url)
    return _jwks_client


async def _verify_api_key(raw_key: str) -> TenantContext:
    """
    Call the IAM's internal verify-api-key endpoint to validate an API key.

    The IAM checks its BetterAuth api_keys table and returns the metadata
    (organizationId, projectId, scopes) stored when the key was created.

    Raises:
        HTTPException 401: Key invalid, revoked, or expired.
        HTTPException 503: IAM unreachable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.iam_url}/api/internal/verify-api-key",
                json={"key": raw_key},
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "IAM_UNAVAILABLE"},
        )

    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY"},
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "IAM_ERROR"},
        )

    data = resp.json()
    return TenantContext(
        organization_id=data.get("organizationId") or "",
        project_id=data.get("projectId"),
        actor_id=data.get("userId") or "",
        scopes=frozenset(data.get("scopes", [])),
        is_test_mode=raw_key.startswith("fn_test_"),
    )


def _verify_jwt(token: str) -> TenantContext:
    """
    Verify a JWT using the IAM's JWKS endpoint.

    Accepts EdDSA (BetterAuth default) and RS256 (compatibility). The issuer and
    audience must match settings.iam_url (BetterAuth sets aud == iss by convention).

    Raises:
        HTTPException 401: Expired, tampered, or malformed token.
    """
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA", "RS256"],
            audience=settings.iam_url,
            issuer=settings.iam_url,
            options={"verify_aud": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN"},
        )

    return TenantContext(
        organization_id=payload.get("org_id") or payload.get("org") or "",
        project_id=payload.get("project_id") or payload.get("project"),
        actor_id=payload.get("sub") or "",
        scopes=frozenset(payload.get("scopes", [])),
    )


async def authenticate_request(request: Request) -> TenantContext:
    """
    FastAPI dependency that resolves a TenantContext from the Authorization header.

    Attach with Depends(authenticate_request) on routes that require auth, or add
    at the router level to protect an entire prefix.

    Raises:
        HTTPException 401: Missing header, invalid token, or IAM error.
        HTTPException 503: IAM unreachable during API key verification.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_CREDENTIALS"},
        )

    token = auth_header.removeprefix("Bearer ")

    if token.startswith(("fn_live_", "fn_test_")):
        ctx = await _verify_api_key(token)
    else:
        ctx = _verify_jwt(token)

    set_tenant_context(ctx)
    return ctx


def require_scope(ctx: TenantContext, scope: str) -> None:
    """
    Assert that the TenantContext includes `scope`. Raises 403 if not.

    Call at the top of each route handler after injecting the context.

    Args:
        ctx:   The resolved TenantContext from authenticate_request.
        scope: Required scope string, e.g. "files:upload".

    Raises:
        HTTPException 403: Scope not present on the token.
    """
    if scope not in ctx.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "required_scope": scope},
        )
