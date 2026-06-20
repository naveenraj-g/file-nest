"""
app.services.storage_config — Business logic for storage configuration.

Handles reading a project's storage config and running the connectivity
verification probe (write + delete a test object against the provider).

Usage:
    svc = StorageConfigService(session=session, ctx=ctx)
    config = await svc.get_config(project_id)
    result = await svc.verify(project_id)
"""
import time
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TenantContext
from app.core.crypto import encrypt_storage_credentials
from app.core.logging import get_logger
from app.repositories.storage_config import StorageConfigRepository
from app.schemas.storage_config import StorageConfigResponse, StorageConfigUpdateRequest, StorageVerifyResponse
from app.storage.resolver import storage_resolver

logger = get_logger(__name__)

_PROBE_KEY_TEMPLATE = "{org}/{project}/.filenest-probe"


class StorageConfigService:
    """
    Handles storage configuration reads and connectivity verification.

    Args:
        session: Active DB session.
        ctx:     Resolved caller identity.
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: StorageConfigRepository,
        ctx: TenantContext,
    ) -> None:
        self._session = session
        self._ctx = ctx
        self._repo = repo

    async def update_config(self, project_id: str, req: StorageConfigUpdateRequest) -> StorageConfigResponse:
        """
        Save BYOB credentials for a project's storage configuration.

        Sensitive fields are AES-256-GCM encrypted before write. After saving,
        status is set to pending_verification — call verify() to promote to active.

        Raises:
            NotFoundError: If no storage config exists for the project.
            StorageError:  If STORAGE_ENCRYPTION_KEY is missing or invalid.
        """
        credentials = {
            "access_key_id": req.access_key_id,
            "secret_access_key": req.secret_access_key,
        }
        if req.kms_key_id:
            credentials["kms_key_id"] = req.kms_key_id

        config_encrypted = encrypt_storage_credentials(credentials)

        record = await self._repo.update(
            project_id,
            self._ctx.organization_id,
            bucket_name=req.bucket_name,
            region=req.region,
            endpoint_url=req.endpoint_url,
            config_encrypted=config_encrypted,
            server_side_encryption=req.server_side_encryption,
            kms_key_id=req.kms_key_id,
        )
        await self._session.commit()

        logger.info(
            "storage_config.updated",
            project_id=project_id,
            organization_id=self._ctx.organization_id,
            provider=record.provider,
        )

        return self._to_response(record)

    async def get_config(self, project_id: str) -> StorageConfigResponse:
        """
        Return the non-sensitive storage configuration for a project.

        Raises:
            NotFoundError: If no storage config exists for the project.
        """
        record = await self._repo.get_for_project(project_id, self._ctx.organization_id)
        return self._to_response(record)

    async def verify(self, project_id: str) -> StorageVerifyResponse:
        """
        Probe the project's storage provider by writing and deleting a test object.

        Updates the config's status and last_verified_at on success.

        Returns:
            StorageVerifyResponse with ok=True and latency_ms on success,
            or ok=False and an error message on failure.
        """
        probe_key = _PROBE_KEY_TEMPLATE.format(
            org=self._ctx.organization_id, project=project_id
        )

        record = await self._repo.get_for_project(project_id, self._ctx.organization_id)
        bucket_name = record.bucket_name or f"fn-{project_id}"
        provider = storage_resolver.get_provider_for_bucket(bucket_name)

        start = time.monotonic()
        try:
            await provider.upload(probe_key, b"filenest-probe", "text/plain")
            await provider.delete_object(probe_key)
            latency_ms = (time.monotonic() - start) * 1000

            await self._repo.update_status(
                project_id,
                self._ctx.organization_id,
                status="active",
                last_verified_at=datetime.now(UTC),
            )
            await self._session.commit()

            logger.info(
                "storage.verified",
                project_id=project_id,
                latency_ms=round(latency_ms, 1),
                organization_id=self._ctx.organization_id,
            )

            return StorageVerifyResponse(ok=True, latency_ms=round(latency_ms, 1))

        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            error_msg = str(exc)

            await self._repo.update_status(
                project_id,
                self._ctx.organization_id,
                status="verification_failed",
            )
            await self._session.commit()

            logger.warning(
                "storage.verify_failed",
                project_id=project_id,
                error=error_msg,
                organization_id=self._ctx.organization_id,
            )

            return StorageVerifyResponse(ok=False, latency_ms=round(latency_ms, 1), error=error_msg)

    def _to_response(self, record) -> StorageConfigResponse:
        return StorageConfigResponse(
            project_id=record.project_id,
            environment=record.environment,
            storage_mode=record.storage_mode,
            provider=record.provider,
            region=record.region,
            bucket_name=record.bucket_name,
            endpoint_url=record.endpoint_url,
            server_side_encryption=record.server_side_encryption,
            status=record.status,
            last_verified_at=record.last_verified_at,
        )
