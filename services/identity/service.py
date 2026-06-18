"""
services.identity.service — Business logic for the Identity Service.

ApiKeyService is the single place where all API key business rules live. It
coordinates between ApiKeyRepository (DB persistence) and the key generation
utilities in shared.auth.token.

Layer rules:
  - Service may call repository and shared auth utilities. No direct SQL.
  - All log calls include organization_id and project_id.

Usage:
    # Constructed via the get_identity_service dependency — not directly.
    svc = ApiKeyService(session=session, ctx=ctx)
    result = await svc.create_api_key(request_body)
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import TenantContext, generate_api_key, require_project_context
from shared.logging import get_logger

from .repository import ApiKeyRepository
from .schemas import ApiKeyListResponse, ApiKeyResponse, CreateApiKeyRequest

logger = get_logger(__name__)


class ApiKeyService:
    """
    Orchestrates all API key business operations for a single request.

    Scoped to one HTTP request via FastAPI's dependency injection. The
    TenantContext is pinned at construction — no method on this class may
    operate outside the org/project boundaries it was given.

    Args:
        session: Active DB session for this request (owns commit/rollback).
        ctx:     Resolved caller identity and permission scopes.
    """

    def __init__(self, session: AsyncSession, ctx: TenantContext) -> None:
        self._session = session
        self._ctx = ctx
        self._repo = ApiKeyRepository(session)

    async def create_api_key(self, req: CreateApiKeyRequest) -> ApiKeyResponse:
        """
        Generate a new API key and persist its hash.

        The raw key is embedded in the response once and cannot be retrieved
        later — the caller must store it immediately.

        Args:
            req: CreateApiKeyRequest with name, scopes, test_mode, expires_in_days.

        Returns:
            ApiKeyResponse with the `key` field populated (one-time only).
        """
        project_id = require_project_context(self._ctx)

        raw_key, key_hash, key_prefix = generate_api_key(test_mode=req.test_mode)

        expires_at = None
        if req.expires_in_days is not None:
            expires_at = datetime.now(UTC) + timedelta(days=req.expires_in_days)

        record = await self._repo.create(
            organization_id=self._ctx.organization_id,
            project_id=project_id,
            name=req.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=req.scopes,
            is_test_mode=req.test_mode,
            expires_at=expires_at,
        )
        await self._session.commit()

        logger.info(
            "api_key.created",
            key_id=record.id,
            name=req.name,
            organization_id=self._ctx.organization_id,
            project_id=project_id,
        )

        return ApiKeyResponse(
            id=record.id,
            name=record.name,
            key_prefix=record.key_prefix,
            key=raw_key,
            scopes=record.scopes,
            is_test_mode=record.is_test_mode,
            is_revoked=record.is_revoked,
            last_used_at=record.last_used_at,
            expires_at=record.expires_at,
            created_at=record.created_at,
        )

    async def list_api_keys(self) -> ApiKeyListResponse:
        """
        Return all API keys for the current project.

        Returns:
            ApiKeyListResponse with all keys (including revoked).
        """
        project_id = require_project_context(self._ctx)

        records = await self._repo.list(self._ctx.organization_id, project_id)
        items = [
            ApiKeyResponse(
                id=r.id,
                name=r.name,
                key_prefix=r.key_prefix,
                key=None,
                scopes=r.scopes,
                is_test_mode=r.is_test_mode,
                is_revoked=r.is_revoked,
                last_used_at=r.last_used_at,
                expires_at=r.expires_at,
                created_at=r.created_at,
            )
            for r in records
        ]
        return ApiKeyListResponse(items=items, total=len(items))

    async def revoke_api_key(self, key_id: str) -> ApiKeyResponse:
        """
        Revoke an API key. Subsequent requests using this key will receive 401.

        Args:
            key_id: UUID of the key to revoke.

        Returns:
            ApiKeyResponse with is_revoked=True.

        Raises:
            NotFoundError: If the key does not exist in this project's scope.
        """
        project_id = require_project_context(self._ctx)

        record = await self._repo.revoke(key_id, self._ctx.organization_id, project_id)
        await self._session.commit()

        logger.info(
            "api_key.revoked",
            key_id=key_id,
            organization_id=self._ctx.organization_id,
            project_id=project_id,
        )

        return ApiKeyResponse(
            id=record.id,
            name=record.name,
            key_prefix=record.key_prefix,
            key=None,
            scopes=record.scopes,
            is_test_mode=record.is_test_mode,
            is_revoked=record.is_revoked,
            last_used_at=record.last_used_at,
            expires_at=record.expires_at,
            created_at=record.created_at,
        )
