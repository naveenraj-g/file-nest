"""
app.auth.dependencies — FastAPI auth dependencies.

Provides:
  - authenticate_request  — resolves a TenantContext from the Bearer token
  - require_scope         — asserts a scope is present on the current context

Token dispatch:
  - fn_live_* / fn_test_*    → POST {IAM_URL}/api/auth/api-key/verify (httpx)
  - fn_upload_token_*         → DB lookup in upload_tokens table
  - JWT (anything else)       → JWKS verification via PyJWT + IAM's /api/auth/jwks

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
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TenantContext, set_tenant_context
from app.core.config import settings
from app.core.database import get_db

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
    Validate an API key via BetterAuth's built-in verify endpoint on the IAM.

    The IAM returns the full api_key record. organizationId is stored as
    referenceId (because the plugin is configured with references="organization").
    projectId and scopes are in metadata, embedded when the key was created.

    Raises:
        HTTPException 401: Key invalid, revoked, or expired.
        HTTPException 503: IAM unreachable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.iam_url}/api/auth/api-key/verify",
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
    key = data.get("key") or {}
    metadata = key.get("metadata") or {}
    return TenantContext(
        organization_id=key.get("referenceId") or metadata.get("organizationId") or "",
        project_id=metadata.get("projectId"),
        actor_id=key.get("userId") or "",
        scopes=frozenset(metadata.get("scopes", [])),
        is_test_mode=raw_key.startswith("fn_test_"),
    )


def _verify_jwt(token: str) -> TenantContext:
    """
    Verify a console-issued JWT using the IAM's JWKS endpoint.

    The IAM embeds the following claims via buildUserContext / definePayload:
      - sub                  → user ID
      - activeOrganizationId → active org for this session
      - permissions[]        → "resource:action" strings from the org role

    JWTs are always org-level (no project_id). project_id comes only from
    project-scoped API keys.

    Raises:
        HTTPException 401: Expired, tampered, or malformed token.
    """
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA", "RS256"],
            options={"verify_aud": False},
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
        organization_id=payload.get("activeOrganizationId") or "",
        project_id=None,
        actor_id=payload.get("sub") or "",
        scopes=frozenset(payload.get("permissions", [])),
    )


async def _verify_upload_token(token: str, session: AsyncSession) -> TenantContext:
    """
    Validate a short-lived browser upload token against the upload_tokens table.

    Upload tokens grant only the files:upload scope and are scoped to the
    specific project they were issued for. Expired tokens are rejected.

    Args:
        token:   The raw bearer token string starting with fn_upload_token_.
        session: Active DB session (provided by the authenticate_request dependency).

    Raises:
        HTTPException 401: Token not found or expired.
    """
    from app.repositories.upload_token import UploadTokenRepository

    repo = UploadTokenRepository(session)
    record = await repo.get_by_token(token)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_UPLOAD_TOKEN"},
        )
    return TenantContext(
        organization_id=record.organization_id,
        project_id=record.project_id,
        actor_id=f"upload_token:{record.id}",
        scopes=frozenset({"files:upload", "files:read"}),
        is_test_mode=False,
    )


async def authenticate_request(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TenantContext:
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
    elif token.startswith("fn_upload_token_"):
        ctx = await _verify_upload_token(token, session)
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
