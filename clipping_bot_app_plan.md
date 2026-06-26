# Clipping Bot Frontend + Python Backend MVP

## Summary

Build a local React/Vite control panel connected to a FastAPI backend that wraps the Python clipping scripts into reusable pipeline modules.

First working flow:

1. Enter a Kick streamer username.
2. Fetch up to 10 recent VODs from the last selected number of months.
3. Select one VOD and choose the number of clips.
4. Download the VOD, extract audio, transcribe it, ask the LLM for ranked candidates, and cut raw MP4 clips.
5. Review progress, candidate metadata, and raw MP4 previews in the frontend.

This version does not do vertical formatting, captions, smart cropping, or final edit polish.

## Project Structure

```txt
clipping_bot/
  backend/
    app/
      main.py
      settings.py
      schemas.py
      jobs.py
      storage.py
      pipeline/
        kick.py
        download.py
        audio.py
        transcribe.py
        analyze.py
        cut.py
    data/
      jobs/
      videos/
      audio/
      transcripts/
      candidates/
      clips/
    requirements.txt

  frontend/
    src/
      api/
      components/
      pages/
      types/
      App.tsx
    package.json
    vite.config.ts
```

Root-level scripts can remain temporarily while their reusable logic moves into `backend/app/pipeline`.

## Backend

- FastAPI backend with in-process background jobs.
- Job state is persisted under `backend/data/jobs/{job_id}/job.json`.
- Each job folder may include:
  - `source.mp4`
  - `audio/chunk_*.mp3`
  - `transcript.json`
  - `candidates.json`
  - `clips/*.mp4`
- Job statuses:
  - `queued`
  - `fetching_vods`
  - `downloading`
  - `extracting_audio`
  - `transcribing`
  - `analyzing`
  - `cutting`
  - `done`
  - `failed`

## API

```txt
GET /api/health
GET /api/kick/videos?username={username}&months={months}
POST /api/jobs
GET /api/jobs
GET /api/jobs/{job_id}
GET /api/jobs/{job_id}/clips/{filename}
```

`POST /api/jobs` accepts:

```json
{
  "vod_url": "string",
  "vod_title": "string",
  "clip_count": 5
}
```

`clip_count` means the top N final ranked clips, not N clips per transcript chunk.

## Frontend

- React + Vite + TypeScript.
- Fixed left sidebar with Dashboard and Jobs pages.
- White and blue Cluely-inspired visual style:
  - soft sky-blue background
  - white panels
  - clean blue buttons
  - airy serif hero heading
  - restrained 8px card radius
- Dashboard includes:
  - Kick username input
  - months input
  - VOD picker capped at 10 results
  - top clip count input
  - job progress panel
  - clip result cards with score, type, hook, reason, timestamps, preview, and download
- Jobs page lists previous local jobs and reopens their results.

## Test Plan

- Run the backend with `uvicorn app.main:app --reload` from `backend/`.
- Confirm `/api/health` returns `{"status":"ok"}`.
- Confirm Kick lookup returns up to 10 VODs.
- Run the frontend with `npm run dev` from `frontend/`.
- Confirm the UI can search VODs, select one, create a job, poll status, and display final clips.
- For full integration, use a short VOD first to avoid a long download/transcription run.

## Assumptions

- Local-only MVP.
- User selects the VOD after lookup.
- OpenAI is used for transcription and clip analysis.
- Raw MP4 timestamp cuts are included now.
- Vertical edits, captions, crop logic, and model comparisons happen later.
- Existing root `.env` provides `OPENAI_API_KEY`.
