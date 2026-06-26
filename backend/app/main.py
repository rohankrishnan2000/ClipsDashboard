from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .dispatch import remote_processing_available
from .jobs import create_job
from .pipeline.kick import fetch_recent_videos
from .publish.tiktok import TikTokClient, TikTokError, TikTokNotConfigured
from .schemas import (
    ConfigResponse,
    CreateJobRequest,
    CreateJobResponse,
    JobsResponse,
    KickVideosResponse,
    TikTokPublishRequest,
    TikTokPublishResponse,
)
from .settings import get_settings
from .storage import job_store
from .storage_backends import get_storage_backend


settings = get_settings()

app = FastAPI(title="Clipping Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_worker_token(x_worker_token: str | None) -> None:
    """Guard dispatched jobs when this instance runs as the cloud worker."""
    if not settings.is_worker or not settings.worker_api_token:
        return
    if not x_worker_token or not secrets.compare_digest(x_worker_token, settings.worker_api_token):
        raise HTTPException(status_code=401, detail="Invalid or missing worker token")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    """Tell the frontend which integrations are wired up so the UI can show
    connect/setup prompts instead of failing silently."""
    return ConfigResponse(
        openai_configured=bool(settings.openai_api_key),
        tiktok_configured=settings.tiktok_configured,
        vultr_configured=settings.vultr_configured,
        worker_configured=remote_processing_available(),
        default_processing_mode=settings.default_processing_mode,
        storage_backend=settings.storage_backend,
    )


@app.get("/api/kick/videos", response_model=KickVideosResponse)
def kick_videos(
    username: str = Query(..., min_length=1),
    months: int = Query(1, ge=1, le=36),
) -> KickVideosResponse:
    try:
        videos = fetch_recent_videos(username, months, limit=10)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch Kick videos: {exc}") from exc
    return KickVideosResponse(username=username.strip().lstrip("@"), videos=videos)


@app.post("/api/jobs", response_model=CreateJobResponse)
def post_job(
    request: CreateJobRequest,
    x_worker_token: str | None = Header(default=None),
) -> CreateJobResponse:
    _require_worker_token(x_worker_token)
    job = create_job(request)
    return CreateJobResponse(job_id=job.job_id, status=job.status)


@app.get("/api/jobs", response_model=JobsResponse)
def list_jobs() -> JobsResponse:
    return JobsResponse(jobs=job_store.list())


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    try:
        return job_store.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@app.get("/api/jobs/{job_id}/clips/{filename}")
def get_clip(job_id: str, filename: str) -> FileResponse:
    clip_path = (job_store.job_dir(job_id) / "clips" / filename).resolve()
    clips_dir = (job_store.job_dir(job_id) / "clips").resolve()
    if clips_dir not in clip_path.parents or not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(Path(clip_path), media_type="video/mp4", filename=filename)


# ── TikTok publishing ────────────────────────────────────────────────


def _clip_public_url(job_id: str, filename: str) -> str:
    """Absolute URL TikTok can pull the clip from."""
    storage = get_storage_backend()
    url = storage.public_url(job_id, filename)
    if url.startswith("http"):
        return url
    base = settings.public_base_url.rstrip("/")
    if not base:
        raise HTTPException(
            status_code=400,
            detail=(
                "PUBLIC_BASE_URL is not set, so TikTok cannot pull the clip. "
                "Set it to this backend's public URL, or use Vultr storage."
            ),
        )
    return f"{base}{url}"


@app.get("/api/tiktok/auth/url")
def tiktok_auth_url(state: str | None = None) -> dict[str, str]:
    try:
        client = TikTokClient(settings)
    except TikTokNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"url": client.authorize_url(state or secrets.token_urlsafe(16))}


@app.get("/api/tiktok/auth/callback")
def tiktok_auth_callback(code: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(status_code=400, detail=f"TikTok auth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    try:
        client = TikTokClient(settings)
        tokens = client.exchange_code(code)
    except (TikTokNotConfigured, TikTokError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # TODO(user): persist `tokens` keyed by the TikTok account so publishing
    # can reuse them. For now they are returned for inspection.
    return {"connected": True, "tokens": tokens}


@app.post("/api/tiktok/publish", response_model=TikTokPublishResponse)
def tiktok_publish(request: TikTokPublishRequest) -> TikTokPublishResponse:
    try:
        client = TikTokClient(settings)
    except TikTokNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    video_url = _clip_public_url(request.job_id, request.filename)
    try:
        result = client.post_from_url(
            request.access_token,
            video_url=video_url,
            caption=request.caption,
            privacy_level=request.privacy_level,
            mode=request.mode,
            disable_comment=request.disable_comment,
            disable_duet=request.disable_duet,
            disable_stitch=request.disable_stitch,
        )
    except TikTokError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return TikTokPublishResponse(
        publish_id=result.publish_id, status=result.status, mode=result.mode
    )
