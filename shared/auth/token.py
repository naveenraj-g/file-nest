"""
shared.auth.token — Token verification helpers for JWT and API keys.

Two verifiers are provided:
  - `verify_jwt`     — validates a HS256 JWT issued by the FileNest backend and
                       extracts org/project/scopes from its claims.
  - `verify_api_key` — looks up a hashed API key in the database and returns
                       the associated TenantContext. (Phase 1: stub only.)

Both raise HTTP 401 on any failure so the caller (authenticate_request) does
not need to handle verification errors.

JWT claim shape expected by verify_jwt:
    {
        "sub":     "<actor_id>",
        "org":     "<organization_id>",
        "project": "<project_id>",
        "scopes":  ["files:upload", ...]   # optional
    }

Usage:
    This module is internal to shared.auth — import from shared.auth instead.
"""
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
        project_id=payload["project"],
        actor_id=payload["sub"],
        scopes=frozenset(payload.get("scopes", [])),
    )


async def verify_api_key(raw_key: str) -> TenantContext:
    """
    Verify a `fn_live_` or `fn_test_` prefixed API key against the database.

    Phase 1 stub — full implementation in the identity service will hash the
    raw key with the configured salt and look it up in the `api_keys` table.

    Args:
        raw_key: The raw API key string including its prefix.

    Raises:
        HTTPException 401: Always, until the identity service is implemented.
    """
    # TODO (Phase 1): hash raw_key + salt, query api_keys table, build context
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_API_KEY"},
    )
