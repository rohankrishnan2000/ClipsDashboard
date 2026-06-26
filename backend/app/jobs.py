from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .pipeline.analyze import analyze_transcript
from .pipeline.audio import extract_audio_chunks
from .pipeline.cut import cut_raw_clips
from .pipeline.download import download_vod
from .pipeline.transcribe import transcribe_audio_chunks
from .schemas import ClipCandidate, CreateJobRequest, JobRecord, JobStatus
from .settings import get_settings
from .storage import job_store


executor = ThreadPoolExecutor(max_workers=1)


def create_job(request: CreateJobRequest) -> JobRecord:
    job = job_store.create_job(request.vod_url, request.vod_title, request.clip_count)
    executor.submit(run_job, job.job_id)
    return job


def run_job(job_id: str) -> None:
    settings = get_settings()
    job = job_store.get(job_id)
    job_dir = job_store.job_dir(job_id)

    if not settings.openai_api_key:
        job_store.update(
            job_id,
            status=JobStatus.failed,
            progress=1.0,
            message="Missing OPENAI_API_KEY in .env",
            error="OPENAI_API_KEY is required for transcription and clip analysis.",
        )
        return

    try:
        job_store.update(job_id, status=JobStatus.downloading, progress=0.08, message="Downloading selected Kick VOD")
        video_path = download_vod(job.vod_url, job_dir)
        job_store.update(job_id, progress=0.25, artifacts={"source_video": str(video_path)})

        job_store.update(job_id, status=JobStatus.extracting_audio, progress=0.32, message="Extracting audio chunks")
        audio_chunks = extract_audio_chunks(video_path, job_dir / "audio", settings.audio_segment_seconds)
        job_store.update(job_id, progress=0.42, artifacts={"audio_chunks": [str(path) for path in audio_chunks]})

        job_store.update(job_id, status=JobStatus.transcribing, progress=0.48, message="Transcribing audio")
        transcript = transcribe_audio_chunks(
            audio_chunks,
            settings.openai_api_key,
            settings.openai_transcription_model,
            settings.audio_segment_seconds,
        )
        transcript_path = job_dir / "transcript.json"
        job_store.write_json(transcript_path, transcript)
        job_store.update(job_id, progress=0.68, artifacts={"transcript": str(transcript_path)})

        job_store.update(job_id, status=JobStatus.analyzing, progress=0.72, message="Finding clip candidates with LLM")
        candidates = analyze_transcript(
            transcript,
            api_key=settings.openai_api_key,
            model=settings.openai_clip_model,
            clip_count=job.clip_count,
            chunk_seconds=settings.llm_chunk_seconds,
        )
        candidates_path = job_dir / "candidates.json"
        job_store.write_json(candidates_path, candidates)
        job_store.update(job_id, progress=0.84, artifacts={"candidates": str(candidates_path)})

        job_store.update(job_id, status=JobStatus.cutting, progress=0.88, message="Cutting raw MP4 clips")
        clips = cut_raw_clips(video_path, candidates.get("clips", []), job_dir / "clips")
        results = [
            ClipCandidate(**clip, clip_url=f"/api/jobs/{job_id}/clips/{clip['filename']}" if clip.get("filename") else None)
            for clip in clips
            if clip.get("filename")
        ]

        job_store.update(
            job_id,
            status=JobStatus.done,
            progress=1.0,
            message=f"Done. Created {len(results)} raw clips.",
            results=results,
        )
    except Exception as exc:
        job_store.update(
            job_id,
            status=JobStatus.failed,
            progress=1.0,
            message="Job failed",
            error=str(exc),
        )
