"""
shared.auth.token — Token verification and generation helpers.

Provides:
  - `verify_jwt`        — decodes a HS256 JWT and extracts tenant context.
  - `verify_api_key`    — hashes the raw key, looks it up in the `api_keys` table.
  - `generate_api_key`  — creates a new raw key + hash pair for storage.
  - `hash_api_key`      — deterministic hash used for both storage and lookup.

Token dispatch in `authenticate_request`:
  - `fn_live_*` / `fn_test_*` → `verify_api_key`
  - anything else              → `verify_jwt`

JWT claim shape expected by `verify_jwt`:
    {
        "sub":     "<actor_id>",
        "org":     "<organization_id>",
        "project": "<project_id>",   # optional — omit for org-level tokens
        "scopes":  ["files:upload", ...]
    }

Usage:
    This module is internal to shared.auth — import from shared.auth instead.
"""
import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.tenant import TenantContext
from shared.config import settings


def hash_api_key(raw_key: str) -> str:
    """
    Return the SHA-256 hex digest of `{salt}:{raw_key}`.

    The salt is taken from `settings.api_key_salt`. The same hash is used when
    storing a new key and when verifying an incoming request — both paths call
    this function to guarantee consistency.

    Args:
        raw_key: The full raw API key string including its prefix.

    Returns:
        64-character lowercase hex string.
    """
    return hashlib.sha256(f"{settings.api_key_salt}:{raw_key}".encode()).hexdigest()


def generate_api_key(*, test_mode: bool = False) -> tuple[str, str, str]:
    """
    Generate a new API key triple: (raw_key, key_hash, key_prefix).

    The raw key is shown to the user exactly once and must never be stored.
    Only the hash goes in the database.

    Args:
        test_mode: If True, key uses the `fn_test_` prefix; otherwise `fn_live_`.

    Returns:
        Tuple of (raw_key, key_hash, key_prefix):
          - raw_key:    Full key to return to the caller once.
          - key_hash:   SHA-256 digest to store in the `api_keys` table.
          - key_prefix: First 20 chars of raw_key — displayed in the console.
    """
    prefix = "fn_test_" if test_mode else "fn_live_"
    raw_key = f"{prefix}{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:20]
    return raw_key, key_hash, key_prefix


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


async def verify_api_key(raw_key: str, db: AsyncSession) -> TenantContext:
    """
    Verify a `fn_live_` or `fn_test_` prefixed API key against the database.

    Hashes the raw key with the configured salt and looks up the `api_keys`
    table. Updates `last_used_at` on successful verification (best-effort —
    failure does not block the request).

    Args:
        raw_key: The raw API key string including its prefix.
        db:      Active database session for the lookup query.

    Returns:
        TenantContext with scopes and tenant IDs from the stored key record.

    Raises:
        HTTPException 401: If the key is not found, is revoked, or has expired.
    """
    # Import here to avoid circular imports at module load time
    from shared.models.api_key import ApiKey

    key_hash = hash_api_key(raw_key)

    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_revoked.is_(False),
        )
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY"},
        )

    now = datetime.now(UTC)
    if record.expires_at is not None and record.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_KEY_EXPIRED"},
        )

    # Best-effort last_used_at update — don't let it block the request
    try:
        await db.execute(
            update(ApiKey)
            .where(ApiKey.id == record.id)
            .values(last_used_at=now)
        )
        await db.commit()
    except Exception:
        await db.rollback()

    return TenantContext(
        organization_id=record.organization_id,
        project_id=record.project_id,
        actor_id=record.id,
        scopes=frozenset(record.scopes),
        is_test_mode=record.is_test_mode,
    )
