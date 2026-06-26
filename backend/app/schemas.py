from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


ProcessingMode = Literal["local", "cloud"]


class JobStatus(StrEnum):
    queued = "queued"
    fetching_vods = "fetching_vods"
    downloading = "downloading"
    extracting_audio = "extracting_audio"
    transcribing = "transcribing"
    analyzing = "analyzing"
    cutting = "cutting"
    done = "done"
    failed = "failed"


class KickVideo(BaseModel):
    id: str
    title: str
    url: str
    created_at: str | None = None
    duration_sec: int | None = None
    thumbnail_url: str | None = None


class KickVideosResponse(BaseModel):
    username: str
    videos: list[KickVideo]


class CreateJobRequest(BaseModel):
    vod_url: str
    vod_title: str
    clip_count: int = Field(default=5, ge=1, le=25)
    # Run the pipeline in-process ("local") or hand off to the remote
    # Vultr VPS worker ("cloud"). Defaults to the server's configured mode.
    processing_mode: ProcessingMode | None = None


class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus


class ClipCandidate(BaseModel):
    start_time: float
    end_time: float
    start_label: str
    end_label: str
    title: str
    hook: str
    reason: str
    score: int | float
    clip_type: str
    filename: str | None = None
    clip_url: str | None = None


class JobRecord(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0
    message: str = ""
    vod_url: str
    vod_title: str
    clip_count: int
    processing_mode: ProcessingMode = "local"
    created_at: str
    updated_at: str
    error: str | None = None
    results: list[ClipCandidate] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class JobsResponse(BaseModel):
    jobs: list[JobRecord]


# ── TikTok publishing ────────────────────────────────────────────────


class TikTokPublishRequest(BaseModel):
    # The clip to publish, identified by job + filename.
    job_id: str
    filename: str
    # Per-account OAuth access token. TODO(user): once token storage is
    # wired up, look this up by `account` instead of passing it in.
    access_token: str
    account: str | None = None
    caption: str = ""
    mode: Literal["direct", "draft"] = "draft"
    privacy_level: Literal[
        "PUBLIC_TO_EVERYONE",
        "MUTUAL_FOLLOW_FRIENDS",
        "FOLLOWER_OF_CREATOR",
        "SELF_ONLY",
    ] = "SELF_ONLY"
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False


class TikTokPublishResponse(BaseModel):
    publish_id: str
    status: str
    mode: str


# ── Integration / config status (for the frontend) ───────────────────


class ConfigResponse(BaseModel):
    openai_configured: bool
    tiktok_configured: bool
    vultr_configured: bool
    worker_configured: bool
    default_processing_mode: ProcessingMode
    storage_backend: str
