from __future__ import annotations

from pathlib import Path

from .base import StorageBackend


class LocalStorage(StorageBackend):
    """Default backend: clips live under the job folder and are served by
    the FastAPI app at /api/jobs/{job_id}/clips/{filename}."""

    def store_clip(self, job_id: str, local_path: Path) -> str:
        # File is already written into the job's clips/ dir by the cutter,
        # so there is nothing to move — just hand back the served URL.
        return self.public_url(job_id, local_path.name)

    def public_url(self, job_id: str, filename: str) -> str:
        return f"/api/jobs/{job_id}/clips/{filename}"
