"""
shared.auth.token — Token verification helpers.

Provides:
  - `verify_jwt`       — decodes a HS256 JWT and extracts tenant context.
  - `verify_api_key`   — calls the IAM's internal verify-api-key endpoint via HTTP.

Token dispatch in `authenticate_request`:
  - `fn_live_*` / `fn_test_*` → `verify_api_key` (IAM call)
  - anything else              → `verify_jwt` (local decode, no network)

JWT claim shape expected by `verify_jwt`:
    {
        "sub":     "<actor_id>",
        "org":     "<organization_id>",
        "project": "<project_id>",   # optional — omit for org-level tokens
        "scopes":  ["files:upload", ...]
    }

API key metadata shape stored in BetterAuth (set at key creation time):
    {
        "organizationId": "<org_id>",
        "projectId":      "<project_id>",   # optional
        "scopes":         ["files:upload", ...]
    }

Usage:
    This module is internal to shared.auth — import from shared.auth instead.
"""
import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from shared.auth.tenant import TenantContext
from shared.config import settings


async def verify_jwt(token: str) -> TenantContext:
    """
    Decode and validate a HS256 JWT, returning the resolved TenantContext.

    Args:
        token: Raw JWT string (without the "Bearer " prefix).

    Returns:
        TenantContext populated from the token's claims.
        `project_id` will be None if the JWT does not include a "project" claim.

    Raises:
        HTTPException 401: If the token is expired, tampered with, or malformed.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN"},
        )

    return TenantContext(
        organization_id=payload["org"],
        project_id=payload.get("project"),
        actor_id=payload["sub"],
        scopes=frozenset(payload.get("scopes", [])),
    )


async def verify_api_key(raw_key: str) -> TenantContext:
    """
    Verify a `fn_live_` or `fn_test_` prefixed API key against the IAM.

    Calls `POST {IAM_URL}/api/internal/verify-api-key` with the raw key.
    The IAM validates the key against BetterAuth's api_keys store and returns
    the metadata (organizationId, projectId, scopes) attached at creation time.

    Args:
        raw_key: The full raw API key string including its prefix.

    Returns:
        TenantContext with scopes and tenant IDs from the IAM response.

    Raises:
        HTTPException 401: If the key is invalid, revoked, or expired.
        HTTPException 503: If the IAM cannot be reached.
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
