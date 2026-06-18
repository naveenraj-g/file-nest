"""
shared.config — Application configuration package.

Re-exports the Settings class and the singleton `settings` object. All
internal packages should import from here, never from the submodule directly.

Usage:
    from shared.config import settings

    print(settings.redis_url)
"""
from .settings import Settings, settings

__all__ = ["Settings", "settings"]
