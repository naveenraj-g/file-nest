# Storage Service — Provider Configuration Guide

## How provider selection works

```
.env: DEFAULT_STORAGE_PROVIDER=s3
          │
          ▼
    StorageResolver._get_default_provider()
          │
          ├── "s3"    → S3StorageProvider(endpoint_url, access_key_id, ...)
          ├── "azure" → AzureStorageProvider(...)   [Phase 7]
          └── "gcs"   → GCSStorageProvider(...)     [Phase 7]
```

In Phase 7, `StorageResolver.get_provider(project_id)` will first check the
project's stored configuration for a per-project BYOB override before falling
back to the default.

---

## S3-compatible provider (`services/storage/providers/s3.py`)

Works with any S3-compatible endpoint. The only differences between backends
are `S3_ENDPOINT_URL` and `S3_FORCE_PATH_STYLE`.

### RustFS (local development)

```env
DEFAULT_STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=rustfsadmin
S3_SECRET_ACCESS_KEY=rustfsadmin
S3_BUCKET_NAME=filenest
S3_REGION=us-east-1
S3_FORCE_PATH_STYLE=true
```

RustFS runs via `just dev` (docker compose). Web console at http://localhost:9001.

### AWS S3 (production)

```env
DEFAULT_STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=                        # leave empty — boto3 uses AWS default
S3_ACCESS_KEY_ID=AKIA...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=filenest-prod
S3_REGION=us-east-1
S3_FORCE_PATH_STYLE=false
```

In production, prefer IAM role credentials over access keys where possible
(set `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` to empty — boto3 will use
the instance role or ECS task role automatically).

### Cloudflare R2

```env
DEFAULT_STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=<r2_access_key>
S3_SECRET_ACCESS_KEY=<r2_secret_key>
S3_BUCKET_NAME=filenest
S3_REGION=auto
S3_FORCE_PATH_STYLE=true
```

### Backblaze B2

```env
DEFAULT_STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
S3_ACCESS_KEY_ID=<b2_key_id>
S3_SECRET_ACCESS_KEY=<b2_application_key>
S3_BUCKET_NAME=filenest
S3_REGION=us-west-004
S3_FORCE_PATH_STYLE=true
```

### DigitalOcean Spaces

```env
DEFAULT_STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
S3_ACCESS_KEY_ID=<spaces_key>
S3_SECRET_ACCESS_KEY=<spaces_secret>
S3_BUCKET_NAME=filenest
S3_REGION=nyc3
S3_FORCE_PATH_STYLE=false
```

---

## Adding a new provider (Phase 7)

1. Create `services/storage/providers/<name>.py`
2. Implement all five methods from `StorageProvider` Protocol:
   - `generate_presigned_upload_url`
   - `generate_presigned_download_url`
   - `delete_object`
   - `object_exists`
   - `copy_object`
3. Add a branch to `StorageResolver._get_default_provider()` in `resolver.py`
4. Add the provider type string to the "supported" list in the StorageError detail
5. Add docs here with the required env vars
6. Add the new provider's dependency to `services/storage/pyproject.toml`

All methods must raise `shared.exceptions.StorageError` on failure — never
let provider-specific exceptions leak into service code.
