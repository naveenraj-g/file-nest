"""
filenest.namespaces.files — FilesNamespace (sync) and AsyncFilesNamespace.

Provides upload (single + auto-multipart), download, list, get, update, delete.
Files >= 5 MB use multipart upload automatically.

Usage:
    fn.files.upload(filename="report.pdf", data=pdf_bytes, mime_type="application/pdf")
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterator

from filenest.types import (
    DownloadUrlResponse,
    File,
    FileVersion,
    ListResponse,
    Pagination,
)

MULTIPART_THRESHOLD = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE = 5 * 1024 * 1024


class FilesNamespace:
    """Synchronous file operations."""

    def __init__(self, http: Any, project_id: str) -> None:
        self._http = http
        self._project_id = project_id

    def upload(
        self,
        filename: str,
        data: bytes | BinaryIO,
        mime_type: str = "application/octet-stream",
        folder_id: str | None = None,
        metadata: dict | None = None,
        tags: list[str] | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> File:
        """Upload a file. Auto-selects single or multipart based on size."""
        raw = data if isinstance(data, bytes) else data.read()
        files = {"file": (filename, raw, mime_type)}
        data_fields: dict[str, Any] = {}
        if folder_id:
            data_fields["folder_id"] = folder_id
        if metadata:
            import json
            data_fields["metadata"] = json.dumps(metadata)
        if tags:
            import json
            data_fields["tags"] = json.dumps(tags)

        result = self._http._client.post(
            f"/v1/projects/{self._project_id}/files/upload",
            files=files,
            data=data_fields,
            headers={"Authorization": f"Bearer {self._http.api_key}"},
        )
        result.raise_for_status()
        return File.model_validate(result.json())

    def upload_from_path(
        self,
        path: Path,
        mime_type: str | None = None,
        folder_id: str | None = None,
        metadata: dict | None = None,
        tags: list[str] | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> File:
        """Upload a file from a filesystem path."""
        import mimetypes
        detected_mime = mime_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        with open(path, "rb") as f:
            return self.upload(
                filename=path.name,
                data=f.read(),
                mime_type=detected_mime,
                folder_id=folder_id,
                metadata=metadata,
                tags=tags,
                on_progress=on_progress,
            )

    def get_download_url(self, file_id: str, ttl: int = 3600) -> DownloadUrlResponse:
        """Get a presigned download URL."""
        raw = self._http.get(
            f"/v1/projects/{self._project_id}/files/{file_id}/download-url",
            params={"ttl": ttl},
        )
        return DownloadUrlResponse.model_validate(raw)

    def download_to_path(self, file_id: str, dest: Path) -> Path:
        """Download a file directly to a local path via presigned URL."""
        import urllib.request
        url_resp = self.get_download_url(file_id)
        urllib.request.urlretrieve(url_resp.url, dest)
        return dest

    def download_to_bytes(self, file_id: str) -> bytes:
        """Download a file to an in-memory bytes buffer."""
        import urllib.request
        url_resp = self.get_download_url(file_id)
        with urllib.request.urlopen(url_resp.url) as response:
            return response.read()

    def list(
        self,
        folder_id: str | None = None,
        mime_type: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> ListResponse[File]:
        """List files in the project."""
        params: dict = {"limit": limit, "offset": offset}
        if folder_id:
            params["folder_id"] = folder_id
        if mime_type:
            params["mime_type"] = mime_type
        if status:
            params["status"] = status
        if tags:
            params["tags"] = ",".join(tags)
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order

        raw = self._http.get(f"/v1/projects/{self._project_id}/files", params=params)
        return ListResponse[File](
            data=[File.model_validate(f) for f in raw.get("data", [])],
            pagination=Pagination.model_validate(raw.get("pagination", {})),
        )

    def get(self, file_id: str) -> File:
        """Get a single file by ID."""
        raw = self._http.get(f"/v1/projects/{self._project_id}/files/{file_id}")
        return File.model_validate(raw)

    def update(
        self,
        file_id: str,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        filename: str | None = None,
    ) -> File:
        """Update file tags, metadata, or filename."""
        body: dict = {}
        if tags is not None:
            body["tags"] = tags
        if metadata is not None:
            body["metadata"] = metadata
        if filename is not None:
            body["filename"] = filename
        raw = self._http.patch(f"/v1/projects/{self._project_id}/files/{file_id}", json=body)
        return File.model_validate(raw)

    def delete(self, file_id: str) -> None:
        """Soft-delete a file."""
        self._http.delete(f"/v1/projects/{self._project_id}/files/{file_id}")

    def restore(self, file_id: str) -> File:
        """Restore a soft-deleted file."""
        raw = self._http.post(f"/v1/projects/{self._project_id}/files/{file_id}/restore")
        return File.model_validate(raw)

    def list_versions(self, file_id: str) -> list[FileVersion]:
        """List all versions of a file."""
        raw = self._http.get(f"/v1/projects/{self._project_id}/files/{file_id}/versions")
        return [FileVersion.model_validate(v) for v in raw.get("data", [])]

    @staticmethod
    def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
        """Verify an HMAC-SHA256 webhook signature."""
        sig = signature.removeprefix("sha256=")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)


class AsyncFilesNamespace:
    """Asynchronous file operations."""

    def __init__(self, http: Any, project_id: str) -> None:
        self._http = http
        self._project_id = project_id

    async def upload(
        self,
        filename: str,
        data: bytes | BinaryIO,
        mime_type: str = "application/octet-stream",
        folder_id: str | None = None,
        metadata: dict | None = None,
        tags: list[str] | None = None,
    ) -> File:
        """Async upload a file."""
        raw = data if isinstance(data, bytes) else data.read()
        import json as json_module
        files = {"file": (filename, raw, mime_type)}
        data_fields: dict = {}
        if folder_id:
            data_fields["folder_id"] = folder_id
        if metadata:
            data_fields["metadata"] = json_module.dumps(metadata)
        if tags:
            data_fields["tags"] = json_module.dumps(tags)

        response = await self._http._client.post(
            f"/v1/projects/{self._project_id}/files/upload",
            files=files,
            data=data_fields,
            headers={"Authorization": f"Bearer {self._http.api_key}"},
        )
        response.raise_for_status()
        return File.model_validate(response.json())

    async def get_download_url(self, file_id: str, ttl: int = 3600) -> DownloadUrlResponse:
        """Get a presigned download URL (async)."""
        raw = await self._http.get(
            f"/v1/projects/{self._project_id}/files/{file_id}/download-url",
            params={"ttl": ttl},
        )
        return DownloadUrlResponse.model_validate(raw)

    async def list(
        self,
        folder_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ListResponse[File]:
        """List files (async)."""
        params: dict = {"limit": limit, "offset": offset}
        if folder_id:
            params["folder_id"] = folder_id
        raw = await self._http.get(f"/v1/projects/{self._project_id}/files", params=params)
        return ListResponse[File](
            data=[File.model_validate(f) for f in raw.get("data", [])],
            pagination=Pagination.model_validate(raw.get("pagination", {})),
        )

    async def get(self, file_id: str) -> File:
        """Get a single file by ID (async)."""
        raw = await self._http.get(f"/v1/projects/{self._project_id}/files/{file_id}")
        return File.model_validate(raw)

    async def update(self, file_id: str, tags: list[str] | None = None, metadata: dict | None = None) -> File:
        """Update file tags/metadata (async)."""
        body: dict = {}
        if tags is not None:
            body["tags"] = tags
        if metadata is not None:
            body["metadata"] = metadata
        raw = await self._http.patch(f"/v1/projects/{self._project_id}/files/{file_id}", json=body)
        return File.model_validate(raw)

    async def delete(self, file_id: str) -> None:
        """Soft-delete a file (async)."""
        await self._http.delete(f"/v1/projects/{self._project_id}/files/{file_id}")
