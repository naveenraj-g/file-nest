"""
app.storage.resolver — StorageResolver: maps a project to its StorageProvider.

Phase 1: always returns the default provider from settings.
Phase 7: will look up a project's BYOB configuration from the DB first.

Usage:
    from app.storage.resolver import storage_resolver

    provider = await storage_resolver.get_provider(project_id)
    url = await provider.generate_presigned_upload_url(key, content_type, size)
"""
from app.core.config import settings
from app.errors import StorageError
from app.storage.provider import StorageProvider
from app.storage.s3 import S3StorageProvider


class StorageResolver:
    """
    Factory that resolves the correct StorageProvider for a project.

    Thread-safe singleton — all provider instances are stateless and safe for
    concurrent async use.
    """

    def __init__(self) -> None:
        self._default_provider: StorageProvider | None = None

    async def get_provider(self, project_id: str, *, environment: str = "live") -> StorageProvider:
        """
        Return the storage provider for the given project.

        Args:
            project_id:  Project UUID. Used for BYOB lookup in Phase 7.
            environment: "live" or "test".

        Returns:
            A ready StorageProvider implementation.

        Raises:
            StorageError: If the configured provider type is unsupported.
        """
        return self._get_default_provider()

    def _get_default_provider(self) -> StorageProvider:
        if self._default_provider is not None:
            return self._default_provider

        provider_type = settings.default_storage_provider.lower()

        if provider_type == "s3":
            self._default_provider = S3StorageProvider(
                endpoint_url=settings.s3_endpoint_url,
                access_key_id=settings.s3_access_key_id,
                secret_access_key=settings.s3_secret_access_key,
                bucket_name=settings.s3_bucket_name,
                region=settings.s3_region,
                force_path_style=settings.s3_force_path_style,
            )
        else:
            raise StorageError(
                f"Unsupported storage provider: '{provider_type}'",
                detail={"configured": provider_type, "supported": ["s3"]},
            )

        return self._default_provider


# Module-level singleton
storage_resolver = StorageResolver()
