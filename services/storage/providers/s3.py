"""
services.storage.providers.s3 — S3-compatible storage provider.

A single implementation that works with any S3-compatible object storage:

| Backend         | S3_ENDPOINT_URL                              | S3_FORCE_PATH_STYLE |
|-----------------|----------------------------------------------|---------------------|
| RustFS (local)  | http://localhost:9000                        | true                |
| MinIO (local)   | http://localhost:9000                        | true                |
| AWS S3          | (empty — boto3 default)                      | false               |
| Cloudflare R2   | https://<account>.r2.cloudflarestorage.com   | true                |
| Backblaze B2    | https://s3.<region>.backblazeb2.com          | true                |
| DigitalOcean    | https://<region>.digitaloceanspaces.com      | false               |

The only difference between providers is the endpoint URL and path-style setting,
both controlled by environment variables — no code changes required to switch.

Usage:
    from services.storage.providers.s3 import S3StorageProvider

    provider = S3StorageProvider(
        endpoint_url="http://localhost:9000",
        access_key_id="rustfsadmin",
        secret_access_key="rustfsadmin",
        bucket_name="filenest",
        region="us-east-1",
        force_path_style=True,
    )
    url = await provider.generate_presigned_upload_url("org/proj/file_id", "image/png", 1024)
"""
import aioboto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from shared.exceptions import StorageError


class S3StorageProvider:
    """
    S3-compatible storage provider backed by aioboto3.

    All methods share a single aioboto3 session created at construction time.
    The session is not thread-safe but is safe for concurrent async use within
    a single event loop — each method opens its own client context.

    Args:
        endpoint_url:     Override the S3 endpoint. None uses the AWS default.
        access_key_id:    AWS/provider access key ID.
        secret_access_key: AWS/provider secret access key.
        bucket_name:      Target bucket for all operations.
        region:           AWS region (or provider region, e.g. "auto" for R2).
        force_path_style: Set True for RustFS, MinIO, and Cloudflare R2.
    """

    def __init__(
        self,
        *,
        endpoint_url: str | None,
        access_key_id: str | None,
        secret_access_key: str | None,
        bucket_name: str,
        region: str,
        force_path_style: bool,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._bucket_name = bucket_name
        self._region = region
        self._force_path_style = force_path_style
        self._session = aioboto3.Session()

    def _client_kwargs(self) -> dict:
        """Build the keyword arguments for creating a boto3 S3 client."""
        kwargs: dict = {
            "region_name": self._region,
            "config": Config(signature_version="s3v4"),
        }
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        if self._access_key_id:
            kwargs["aws_access_key_id"] = self._access_key_id
        if self._secret_access_key:
            kwargs["aws_secret_access_key"] = self._secret_access_key
        # force_path_style is required for RustFS/MinIO/R2 where bucket is
        # identified by path segment, not subdomain
        if self._force_path_style:
            kwargs["config"] = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            )
        return kwargs

    async def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        size_bytes: int,
        *,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned PUT URL for direct client-to-storage uploads.

        The client must send a PUT request (not POST) to this URL with the file
        bytes and the matching Content-Type header.

        Args:
            key:          Object storage key, e.g. "org_123/proj_456/file_789".
            content_type: MIME type — enforced by the presigned URL signature.
            size_bytes:   Unused for PUT presign but kept for API consistency.
            expires_in:   URL validity in seconds.

        Returns:
            Presigned PUT URL string.

        Raises:
            StorageError: If the provider returns an error.
        """
        try:
            async with self._session.client("s3", **self._client_kwargs()) as s3:
                url: str = await s3.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": self._bucket_name,
                        "Key": key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=expires_in,
                )
            return url
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(
                f"Failed to generate presigned upload URL for key '{key}'",
                detail={"key": key, "provider_error": str(exc)},
            ) from exc

    async def generate_presigned_download_url(
        self,
        key: str,
        *,
        filename: str | None = None,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned GET URL for downloading an object.

        Args:
            key:        Object storage key.
            filename:   If provided, sets Content-Disposition: attachment; filename=<filename>.
            expires_in: URL validity in seconds.

        Returns:
            Presigned GET URL string.

        Raises:
            StorageError: If the provider returns an error.
        """
        params: dict = {"Bucket": self._bucket_name, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        try:
            async with self._session.client("s3", **self._client_kwargs()) as s3:
                url: str = await s3.generate_presigned_url(
                    "get_object",
                    Params=params,
                    ExpiresIn=expires_in,
                )
            return url
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(
                f"Failed to generate presigned download URL for key '{key}'",
                detail={"key": key, "provider_error": str(exc)},
            ) from exc

    async def delete_object(self, key: str) -> None:
        """
        Delete an object. Silently succeeds if the object does not exist.

        Args:
            key: Object storage key.

        Raises:
            StorageError: On unexpected provider errors.
        """
        try:
            async with self._session.client("s3", **self._client_kwargs()) as s3:
                await s3.delete_object(Bucket=self._bucket_name, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(
                f"Failed to delete object '{key}'",
                detail={"key": key, "provider_error": str(exc)},
            ) from exc

    async def object_exists(self, key: str) -> bool:
        """
        Return True if the object exists in the bucket (uses head_object).

        Args:
            key: Object storage key.

        Returns:
            True if the object exists and is accessible.

        Raises:
            StorageError: On unexpected provider errors (not 404).
        """
        try:
            async with self._session.client("s3", **self._client_kwargs()) as s3:
                await s3.head_object(Bucket=self._bucket_name, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise StorageError(
                f"Unexpected error checking existence of '{key}'",
                detail={"key": key, "provider_error": str(exc)},
            ) from exc
        except BotoCoreError as exc:
            raise StorageError(
                f"Failed to check existence of '{key}'",
                detail={"key": key, "provider_error": str(exc)},
            ) from exc

    async def copy_object(self, source_key: str, dest_key: str) -> None:
        """
        Copy an object within the bucket (used for versioning in Phase 3).

        Args:
            source_key: Storage key of the source.
            dest_key:   Storage key for the copy.

        Raises:
            StorageError: If the copy fails.
        """
        try:
            async with self._session.client("s3", **self._client_kwargs()) as s3:
                await s3.copy_object(
                    Bucket=self._bucket_name,
                    CopySource={"Bucket": self._bucket_name, "Key": source_key},
                    Key=dest_key,
                )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(
                f"Failed to copy '{source_key}' to '{dest_key}'",
                detail={"source": source_key, "dest": dest_key, "provider_error": str(exc)},
            ) from exc
