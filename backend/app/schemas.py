from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


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
    created_at: str
    updated_at: str
    error: str | None = None
    results: list[ClipCandidate] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class JobsResponse(BaseModel):
    jobs: list[JobRecord]
