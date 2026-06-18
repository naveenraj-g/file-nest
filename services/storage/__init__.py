"""
services.storage — Pluggable object storage abstraction.

Exposes two public objects:
  - StorageProvider  — the Protocol (interface) that all backends satisfy
  - storage_resolver — singleton StorageResolver; call get_provider() to get a provider

Service code should only import from this package, never from sub-modules directly.

Usage:
    from services.storage import storage_resolver

    provider = await storage_resolver.get_provider(project_id)
    url = await provider.generate_presigned_upload_url(key, content_type, size_bytes)
"""
from .provider import StorageProvider
from .resolver import StorageResolver, storage_resolver

__all__ = ["StorageProvider", "StorageResolver", "storage_resolver"]
