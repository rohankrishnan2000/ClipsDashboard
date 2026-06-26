"""Remote processing dispatch (the "cloud" option).

When a job is created with `processing_mode="cloud"`, the heavy work
(download → audio → transcribe → analyze → cut) should run on a beefier
machine — a Vultr VPS running this same backend with IS_WORKER=true — so
the user's laptop / a serverless host doesn't have to.

This module is the thin client that forwards a job to that worker. The
worker is just another instance of this FastAPI app reachable at
WORKER_URL, protected by a shared WORKER_API_TOKEN.

Architecture (groundwork — wire up once your VPS is online):

    Frontend ──POST /api/jobs {processing_mode:"cloud"}──▶ API host
        API host ──dispatch_remote_job()──▶  Vultr VPS worker
            worker runs pipeline, uploads clips to Vultr storage
        Frontend polls GET /api/jobs/{id} (proxied to the worker)

For a more robust setup you can later replace the direct HTTP hand-off
with a real queue (Redis + RQ/Celery). The seam is intentionally small.
"""

from __future__ import annotations

import requests

from .schemas import CreateJobRequest
from .settings import get_settings


class WorkerNotConfigured(RuntimeError):
    pass


def remote_processing_available() -> bool:
    return get_settings().worker_configured


def dispatch_remote_job(request: CreateJobRequest) -> dict:
    """Forward a job to the remote worker and return its {job_id, status}.

    Raises WorkerNotConfigured if WORKER_URL is unset.
    """
    settings = get_settings()
    if not settings.worker_configured:
        raise WorkerNotConfigured(
            "Cloud processing requested but WORKER_URL is not set. "
            "Stand up a Vultr VPS worker and set WORKER_URL (see TODO.md)."
        )

    headers = {"Content-Type": "application/json"}
    if settings.worker_api_token:
        headers["X-Worker-Token"] = settings.worker_api_token

    # Force the worker to run locally on the VPS (avoid infinite forwarding).
    body = request.model_dump()
    body["processing_mode"] = "local"

    resp = requests.post(
        f"{settings.worker_url.rstrip('/')}/api/jobs",
        json=body,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
