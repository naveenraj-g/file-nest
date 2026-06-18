"""
services.storage.provider — StorageProvider Protocol (interface).

Defines the contract that every storage backend must satisfy. All service code
that touches object storage must depend on this Protocol — never on a concrete
provider class such as S3StorageProvider directly.

This makes it possible to swap the underlying storage (RustFS → AWS S3 → Azure
Blob → GCS → Cloudflare R2) by changing configuration, not code.

Implementing a new provider:
  1. Create services/storage/providers/<name>.py
  2. Implement the StorageProvider Protocol (structural subtyping — no base class needed)
  3. Register it in StorageResolver._build_provider()

Usage:
    from services.storage.provider import StorageProvider

    # Type-hint a provider reference in service code
    provider: StorageProvider = await resolver.get_provider(project_id)
    url = await provider.generate_presigned_upload_url(key, content_type, size_bytes)
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageProvider(Protocol):
    """
    Structural interface for all FileNest storage backends.

    Every method is async. Implementations must be safe for concurrent use
    (all S3-compatible clients satisfy this via connection pooling).

    Implementations must raise `shared.exceptions.StorageError` on unexpected
    failures — never propagate provider-specific exceptions to callers.
    """

    async def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        size_bytes: int,
        *,
        expires_in: int = 3600,
    ) -> str:
        """
        Return a presigned URL that allows a client to PUT an object directly to storage.

        The URL is single-use and scoped to the given key. The client must set
        the Content-Type header to match `content_type` when using the URL.

        Args:
            key:          Storage key (path) for the object, e.g. "org/proj/file_id".
            content_type: MIME type the client will set on the PUT request.
            size_bytes:   Expected file size — used by some providers for validation.
            expires_in:   URL TTL in seconds (default 1 hour).

        Returns:
            A presigned HTTPS URL string.

        Raises:
            StorageError: If the provider cannot generate the URL.
        """
        ...

    async def generate_presigned_download_url(
        self,
        key: str,
        *,
        filename: str | None = None,
        expires_in: int = 3600,
    ) -> str:
        """
        Return a presigned URL that allows a client to GET an object from storage.

        Args:
            key:        Storage key of the object to download.
            filename:   Optional Content-Disposition filename override.
            expires_in: URL TTL in seconds (default 1 hour).

        Returns:
            A presigned HTTPS URL string.

        Raises:
            StorageError: If the provider cannot generate the URL.
        """
        ...

    async def delete_object(self, key: str) -> None:
        """
        Permanently delete an object from storage.

        No-op if the object does not exist (idempotent).

        Args:
            key: Storage key of the object to delete.

        Raises:
            StorageError: If the deletion fails for reasons other than not-found.
        """
        ...

    async def object_exists(self, key: str) -> bool:
        """
        Check whether an object exists in storage without downloading it.

        Used by the upload-confirm flow to verify the client's PUT succeeded.

        Args:
            key: Storage key to check.

        Returns:
            True if the object exists and is accessible.

        Raises:
            StorageError: If the provider returns an unexpected error.
        """
        ...

    async def copy_object(self, source_key: str, dest_key: str) -> None:
        """
        Copy an object within the same bucket (used for versioning, Phase 3).

        Args:
            source_key: Storage key of the source object.
            dest_key:   Storage key for the copy.

        Raises:
            StorageError: If the copy fails.
        """
        ...
