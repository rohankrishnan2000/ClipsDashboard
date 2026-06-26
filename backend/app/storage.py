from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from .schemas import ClipCandidate, JobRecord, JobStatus
from .settings import get_settings


class JobStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.jobs_dir = self.settings.data_dir / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def create_job(self, vod_url: str, vod_title: str, clip_count: int) -> JobRecord:
        now = self._now()
        job = JobRecord(
            job_id=uuid4().hex[:12],
            status=JobStatus.queued,
            progress=0.0,
            message="Queued",
            vod_url=vod_url,
            vod_title=vod_title,
            clip_count=clip_count,
            created_at=now,
            updated_at=now,
        )
        self.job_dir(job.job_id).mkdir(parents=True, exist_ok=True)
        (self.job_dir(job.job_id) / "clips").mkdir(parents=True, exist_ok=True)
        self.save(job)
        return job

    def job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def job_file(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "job.json"

    def get(self, job_id: str) -> JobRecord:
        path = self.job_file(job_id)
        if not path.exists():
            raise FileNotFoundError(job_id)
        return JobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[JobRecord]:
        jobs: list[JobRecord] = []
        for path in self.jobs_dir.glob("*/job.json"):
            try:
                jobs.append(JobRecord.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return sorted(jobs, key=lambda job: job.created_at, reverse=True)

    def save(self, job: JobRecord) -> None:
        with self._lock:
            job.updated_at = self._now()
            self.job_file(job.job_id).write_text(
                job.model_dump_json(indent=2),
                encoding="utf-8",
            )

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: float | None = None,
        message: str | None = None,
        error: str | None = None,
        results: list[ClipCandidate] | None = None,
        artifacts: dict | None = None,
    ) -> JobRecord:
        job = self.get(job_id)
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if message is not None:
            job.message = message
        if error is not None:
            job.error = error
        if results is not None:
            job.results = results
        if artifacts is not None:
            job.artifacts.update(artifacts)
        self.save(job)
        return job

    @staticmethod
    def write_json(path: Path, data: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def read_json(path: Path) -> object:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()


job_store = JobStore()
