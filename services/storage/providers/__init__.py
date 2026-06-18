"""
services.storage.providers — Concrete storage provider implementations.

Each submodule implements the StorageProvider Protocol for a specific backend:
  - s3.py  — AWS S3, RustFS, MinIO, Cloudflare R2, Backblaze B2 (all S3-compatible)
  - azure.py — Azure Blob Storage (Phase 7)
  - gcs.py   — Google Cloud Storage (Phase 7)

Import providers through StorageResolver — not directly in service code.
"""
from .s3 import S3StorageProvider

__all__ = ["S3StorageProvider"]
