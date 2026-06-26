from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    # ── Core / OpenAI ────────────────────────────────────────────────
    openai_api_key: str | None = None
    openai_transcription_model: str = "whisper-1"
    openai_clip_model: str = "gpt-4.1-mini"
    data_dir: Path = BACKEND_DIR / "data"
    frontend_origin: str = "http://localhost:5173"
    # Comma-separated list of additional allowed CORS origins (e.g. your
    # Vercel URL). Example: "https://clips.vercel.app,https://www.example.com"
    extra_cors_origins: str = ""
    llm_chunk_seconds: int = 600
    audio_segment_seconds: int = 600

    # Public base URL of THIS backend, used to build absolute clip URLs
    # (e.g. for TikTok PULL_FROM_URL). On the Vultr VPS set this to the
    # backend's public https URL. Leave blank for local dev.
    public_base_url: str = ""

    # ── Processing mode / remote worker (Vultr VPS) ──────────────────
    # "local"  -> run the pipeline in this process.
    # "cloud"  -> dispatch the job to a remote worker (the same backend
    #             deployed on a Vultr VPS) via WORKER_URL.
    default_processing_mode: Literal["local", "cloud"] = "local"
    # Base URL of the remote worker backend running on the Vultr VPS.
    worker_url: str = ""
    # Shared secret sent as `X-Worker-Token` so only your services can
    # dispatch jobs to the worker. Set the same value on both ends.
    worker_api_token: str = ""
    # When true, THIS process is the remote worker and will accept
    # dispatched jobs. Set on the Vultr VPS deployment.
    is_worker: bool = False

    # ── Storage backend (clips / artifacts) ──────────────────────────
    # "local"  -> store under data/ on disk (default for dev).
    # "vultr"  -> upload clips to Vultr Object Storage (S3-compatible).
    storage_backend: Literal["local", "vultr"] = "local"
    # Vultr Object Storage is S3-compatible. Find these in the Vultr
    # control panel under "Object Storage".
    vultr_s3_endpoint: str = ""  # e.g. https://ewr1.vultrobjects.com
    vultr_s3_region: str = "us-east-1"
    vultr_s3_bucket: str = ""
    vultr_s3_access_key: str = ""
    vultr_s3_secret_key: str = ""
    # Optional public CDN/base URL for served objects. If blank, the
    # endpoint+bucket is used to build object URLs.
    vultr_public_base_url: str = ""

    # ── TikTok Content Posting API ───────────────────────────────────
    # Create an app at https://developers.tiktok.com/ and request the
    # "Content Posting API" scopes (video.publish / video.upload).
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    # Where TikTok redirects after OAuth; must match the app settings.
    tiktok_redirect_uri: str = "http://localhost:8000/api/tiktok/auth/callback"
    # Scopes requested during OAuth.
    tiktok_scopes: str = "user.info.basic,video.publish,video.upload"

    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Convenience flags so callers can show "configured" state ─────
    @property
    def tiktok_configured(self) -> bool:
        return bool(self.tiktok_client_key and self.tiktok_client_secret)

    @property
    def vultr_configured(self) -> bool:
        return bool(
            self.vultr_s3_endpoint
            and self.vultr_s3_bucket
            and self.vultr_s3_access_key
            and self.vultr_s3_secret_key
        )

    @property
    def worker_configured(self) -> bool:
        return bool(self.worker_url)

    def cors_origins(self) -> list[str]:
        origins = {self.frontend_origin, "http://127.0.0.1:5173", "http://localhost:3000"}
        for origin in self.extra_cors_origins.split(","):
            origin = origin.strip()
            if origin:
                origins.add(origin)
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
