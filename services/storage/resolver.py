"""
services.storage.resolver — StorageResolver: maps a project to its storage provider.

The resolver is the single factory responsible for deciding which StorageProvider
implementation to use for a given project. In Phase 1 it always returns the
default provider from settings. In Phase 7+, it will look up a project's stored
configuration to honour BYOB (Bring Your Own Bucket) setups.

Resolution order (Phase 1 → Phase 7):
  1. Project-level override stored in DB (Phase 7 — not yet implemented)
  2. Default provider from `settings.default_storage_provider`

This means service code never needs to import or construct a provider directly —
it always calls StorageResolver.get_provider() and receives a StorageProvider.

Usage:
    from services.storage.resolver import StorageResolver

    resolver = StorageResolver()
    provider = await resolver.get_provider(project_id="proj_123")
    url = await provider.generate_presigned_upload_url(key, content_type, size)
"""
from shared.config import settings
from shared.exceptions import StorageError

from .provider import StorageProvider
from .providers.s3 import S3StorageProvider


class StorageResolver:
    """
    Factory that resolves the correct StorageProvider for a project.

    Phase 1: always returns a provider built from the global settings.
    Phase 7: will query the project's stored storage configuration first
             and fall back to the global default.

    Can be used as a singleton (one instance per service process) since all
    provider instances are stateless and safe for concurrent async use.
    """

    def __init__(self) -> None:
        # Cache the default provider so we don't reconstruct it on every request
        self._default_provider: StorageProvider | None = None

    async def get_provider(
        self,
        project_id: str,
        *,
        environment: str = "live",
    ) -> StorageProvider:
        """
        Return the storage provider configured for the given project.

        Args:
            project_id:  The project UUID. Used for BYOB lookup in Phase 7.
            environment: "live" or "test" — test mode may use a separate bucket.

        Returns:
            A StorageProvider implementation ready for use.

        Raises:
            StorageError: If the configured provider type is unsupported.
        """
        # Phase 7: add DB lookup here for project-level BYOB configuration
        # For now, always return the global default
        return self._get_default_provider()

    def _get_default_provider(self) -> StorageProvider:
        """
        Build (or return cached) the default provider from application settings.

        Raises:
            StorageError: If `default_storage_provider` names an unsupported backend.
        """
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
        # Phase 7: add "azure" and "gcs" branches here
        else:
            raise StorageError(
                f"Unsupported storage provider: '{provider_type}'",
                detail={"configured": provider_type, "supported": ["s3"]},
            )

        return self._default_provider


# Module-level singleton — import and use this in service code
storage_resolver = StorageResolver()
