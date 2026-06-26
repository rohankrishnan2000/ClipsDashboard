from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .jobs import create_job
from .pipeline.kick import fetch_recent_videos
from .schemas import CreateJobRequest, CreateJobResponse, JobsResponse, KickVideosResponse
from .settings import get_settings
from .storage import job_store


settings = get_settings()

app = FastAPI(title="Clipping Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
def post_job(request: CreateJobRequest) -> CreateJobResponse:
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
