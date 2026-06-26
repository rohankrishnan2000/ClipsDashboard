from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    """Abstract place to put generated clips / artifacts.

    Two implementations exist:
      - LocalStorage: keeps files on disk and serves them through the API.
      - VultrStorage: uploads to Vultr Object Storage (S3-compatible) and
        returns a public URL.

    Swapping between them is controlled by STORAGE_BACKEND in settings.
    """

    @abstractmethod
    def store_clip(self, job_id: str, local_path: Path) -> str:
        """Persist a finished clip and return a URL the frontend can use.

        For local storage this is the same-origin `/api/jobs/.../clips/...`
        path; for cloud storage it is the object's public https URL.
        """

    @abstractmethod
    def public_url(self, job_id: str, filename: str) -> str:
        """Return the URL for an already-stored clip without re-uploading."""
