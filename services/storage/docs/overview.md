# Storage Service — Overview

## Purpose

The storage package provides a pluggable abstraction over object storage backends. All file services interact with storage through the `StorageProvider` Protocol and the `StorageResolver` singleton — never by instantiating a provider directly.

This makes the storage backend a configuration concern, not a code concern. Switching from RustFS to AWS S3 to Azure Blob requires only environment variable changes.

## Supported backends

| Backend | `DEFAULT_STORAGE_PROVIDER` | Requires |
|---------|---------------------------|---------|
| RustFS (local dev) | `s3` | `S3_ENDPOINT_URL=http://localhost:9000`, `S3_FORCE_PATH_STYLE=true` |
| MinIO (local dev) | `s3` | `S3_ENDPOINT_URL=http://localhost:9000`, `S3_FORCE_PATH_STYLE=true` |
| AWS S3 | `s3` | `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_FORCE_PATH_STYLE=false` |
| Cloudflare R2 | `s3` | `S3_ENDPOINT_URL=https://<acct>.r2.cloudflarestorage.com`, `S3_FORCE_PATH_STYLE=true` |
| Backblaze B2 | `s3` | `S3_ENDPOINT_URL=https://s3.<region>.backblazeb2.com` |
| Azure Blob | `azure` | Phase 7 |
| Google Cloud Storage | `gcs` | Phase 7 |

## Package layout

```
services/storage/
├── provider.py          — StorageProvider Protocol (interface)
├── resolver.py          — StorageResolver: picks provider per project
├── providers/
│   ├── s3.py            — S3-compatible provider (RustFS, AWS S3, R2, MinIO)
│   ├── azure.py         — Azure Blob Storage (Phase 7)
│   └── gcs.py           — Google Cloud Storage (Phase 7)
└── docs/                — this folder
```

## Usage in service code

```python
from services.storage import storage_resolver

provider = await storage_resolver.get_provider(project_id=ctx.project_id)

# Generate a presigned upload URL
upload_url = await provider.generate_presigned_upload_url(
    key="org_123/proj_456/file_789",
    content_type="image/png",
    size_bytes=1024,
    expires_in=3600,
)

# Generate a presigned download URL
download_url = await provider.generate_presigned_download_url(
    key="org_123/proj_456/file_789",
    filename="photo.png",
    expires_in=3600,
)

# Check if upload succeeded
exists = await provider.object_exists("org_123/proj_456/file_789")

# Delete
await provider.delete_object("org_123/proj_456/file_789")
```

## Patterns & rules

- **Never import** a concrete provider (`S3StorageProvider`, etc.) in service code — always go through `storage_resolver`.
- **Object keys** follow the format `{organization_id}/{project_id}/{file_id}` — namespaced so all tenants share one bucket without ACL complexity.
- All provider methods raise `shared.exceptions.StorageError` on failure — never provider-specific exceptions.
- The `storage_resolver` singleton is safe for concurrent async use — it caches the default provider after first construction.
