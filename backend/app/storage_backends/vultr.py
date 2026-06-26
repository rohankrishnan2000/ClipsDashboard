from __future__ import annotations

from pathlib import Path

from ..settings import Settings
from .base import StorageBackend


class VultrStorage(StorageBackend):
    """Upload clips to Vultr Object Storage (S3-compatible).

    Requires `boto3` (already in requirements) and the VULTR_S3_* settings.
    Objects are stored under `clips/{job_id}/{filename}` and made public so
    they can be previewed in the browser and pulled by TikTok.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.vultr_configured:
            raise RuntimeError(
                "Vultr storage selected but VULTR_S3_* settings are incomplete. "
                "See TODO.md / .env.example."
            )
        # Imported lazily so the dependency is only needed when this
        # backend is actually used.
        import boto3  # type: ignore

        self.settings = settings
        self.bucket = settings.vultr_s3_bucket
        self._client = boto3.client(
            "s3",
            region_name=settings.vultr_s3_region,
            endpoint_url=settings.vultr_s3_endpoint,
            aws_access_key_id=settings.vultr_s3_access_key,
            aws_secret_access_key=settings.vultr_s3_secret_key,
        )

    def _key(self, job_id: str, filename: str) -> str:
        return f"clips/{job_id}/{filename}"

    def store_clip(self, job_id: str, local_path: Path) -> str:
        key = self._key(job_id, local_path.name)
        self._client.upload_file(
            str(local_path),
            self.bucket,
            key,
            ExtraArgs={"ACL": "public-read", "ContentType": "video/mp4"},
        )
        return self.public_url(job_id, local_path.name)

    def public_url(self, job_id: str, filename: str) -> str:
        key = self._key(job_id, filename)
        base = self.settings.vultr_public_base_url.rstrip("/")
        if base:
            return f"{base}/{key}"
        endpoint = self.settings.vultr_s3_endpoint.rstrip("/")
        # Vultr serves objects at {endpoint}/{bucket}/{key}
        return f"{endpoint}/{self.bucket}/{key}"
