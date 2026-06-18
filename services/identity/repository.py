"""
services.identity.repository — Database access layer for the Identity Service.

ApiKeyRepository is the ONLY place in the identity service that issues SQL.
Every query includes organization_id and project_id filters to enforce
multi-tenant isolation.

Rules:
  - No business logic. Conditionals belong in service.py.
  - Use db.flush() after inserts to get DB-assigned IDs without committing.
  - Revoked keys are never deleted — set is_revoked = True instead.

Usage:
    from services.identity.repository import ApiKeyRepository
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import NotFoundError
from shared.models.api_key import ApiKey


class ApiKeyRepository:
    """
    Async repository for ApiKey CRUD operations.

    Every method scopes queries to (organization_id, project_id) to prevent
    cross-tenant access.

    Args:
        session: Active SQLAlchemy AsyncSession for the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> ApiKey:
        """
        Insert a new ApiKey row and flush to obtain the DB-assigned id.

        Args:
            **kwargs: Column values — must include organization_id, project_id,
                      name, key_hash, key_prefix, scopes.

        Returns:
            The persisted ApiKey with id populated.
        """
        record = ApiKey(**kwargs)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get(self, key_id: str, organization_id: str, project_id: str) -> ApiKey:
        """
        Fetch a single API key by ID within the caller's tenant scope.

        Args:
            key_id:          UUID of the API key.
            organization_id: Must match the record's organization_id.
            project_id:      Must match the record's project_id.

        Returns:
            The matching ApiKey.

        Raises:
            NotFoundError: If no matching record exists or it belongs to another tenant.
        """
        result = await self._session.execute(
            select(ApiKey).where(
                ApiKey.id == key_id,
                ApiKey.organization_id == organization_id,
                ApiKey.project_id == project_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundError(f"API key {key_id} not found")
        return record

    async def list(self, organization_id: str, project_id: str) -> list[ApiKey]:
        """
        Return all API keys for a project, ordered by creation date descending.

        Includes revoked keys — callers can filter by is_revoked if needed.

        Args:
            organization_id: Tenant filter.
            project_id:      Project filter.

        Returns:
            List of ApiKey instances, newest first.
        """
        result = await self._session.execute(
            select(ApiKey)
            .where(
                ApiKey.organization_id == organization_id,
                ApiKey.project_id == project_id,
            )
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, key_id: str, organization_id: str, project_id: str) -> ApiKey:
        """
        Mark an API key as revoked. Does not delete the row.

        Args:
            key_id:          UUID of the key to revoke.
            organization_id: Tenant filter.
            project_id:      Project filter.

        Returns:
            The updated ApiKey record with is_revoked=True.

        Raises:
            NotFoundError: If the key does not exist in this tenant's scope.
        """
        record = await self.get(key_id, organization_id, project_id)
        record.is_revoked = True
        return record
