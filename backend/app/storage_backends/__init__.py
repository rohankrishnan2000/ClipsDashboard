from __future__ import annotations

from functools import lru_cache

from ..settings import get_settings
from .base import StorageBackend
from .local import LocalStorage


@lru_cache
def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "vultr":
        from .vultr import VultrStorage

        return VultrStorage(settings)
    return LocalStorage()


__all__ = ["StorageBackend", "LocalStorage", "get_storage_backend"]
