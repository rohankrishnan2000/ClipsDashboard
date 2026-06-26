# SETUP_TODO — what you need to do yourself

This release adds **clip generation in the web app**, **Vercel deployment
config**, and **groundwork** for: posting to TikTok (direct + drafts),
storing videos on a Vultr VPS / Object Storage, and running the
download → transcribe → cut pipeline **locally or on the cloud**.

Everything is wired so you only need to plug in credentials and stand up
the hosts. Each item below says exactly which env var / setting to fill.

Env templates live at `backend/.env.example` and `frontend/.env.example`.
Copy them to `.env` / `.env.local` and fill in the blanks.

---

## 1. Deploy the frontend on Vercel ✅ (config done — do this)

The Next.js app lives in the **`frontend/`** subfolder, which is almost
certainly why your current Vercel deploy fails ("No Next.js version
detected" / "no package.json"). Fix:

1. In the Vercel project → **Settings → General → Root Directory**, set it
   to **`frontend`**. (This is the key fix — Vercel can't auto-detect a
   Next app in a subdirectory.)
2. **Settings → Environment Variables**, add:
   - `BACKEND_URL` = the public URL of your backend (see §2), e.g.
     `https://api.yourdomain.com`. Without it, the deployed site loads but
     API calls (search, jobs) won't reach a backend.
3. Redeploy.

Already handled for you:
- `frontend/vercel.json` (framework + build/install commands)
- `next.config.ts` no longer proxies to `localhost:8000` in production —
  it only proxies when `BACKEND_URL` is set, so the build won't 502.
- `frontend/.env.example` documents `BACKEND_URL`.

> Note: Vercel only hosts the **frontend**. The Python backend (FFmpeg,
> yt-dlp, Whisper) cannot run on Vercel — host it on the Vultr VPS (§4).

---

## 2. Backend hosting + OpenAI (required for clips to actually generate)

The clip pipeline runs in the FastAPI backend (`backend/`). It needs
FFmpeg and Python and is **already fully working locally**.

To do:
1. Set `OPENAI_API_KEY` in `backend/.env` (used for Whisper transcription
   and LLM clip ranking). Optional: `OPENAI_TRANSCRIPTION_MODEL`,
   `OPENAI_CLIP_MODEL`.
2. Install FFmpeg on whatever host runs the backend (`apt install ffmpeg`).
3. Run it: `cd backend && pip install -r requirements.txt &&
   uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Put it behind HTTPS (a domain + reverse proxy) and set that URL as
   `BACKEND_URL` in Vercel, and as `PUBLIC_BASE_URL` in `backend/.env`.
5. Add your Vercel domain to `EXTRA_CORS_ORIGINS` in `backend/.env`
   (comma-separated) so the browser can call the API.

Local dev quickstart is unchanged: backend on `:8000`, `npm run dev` on
the frontend, which proxies `/api/*` to the backend.

---

## 3. Post clips to TikTok — direct or drafts (groundwork done)

Code: `backend/app/publish/tiktok.py`, endpoints in `backend/app/main.py`
(`/api/tiktok/...`), and the **Publish** button + sheet on the Jobs page.

What works already: choosing **Drafts/inbox** vs **Direct post**, caption,
privacy level, and the API call to TikTok's Content Posting API
(`PULL_FROM_URL`).

To do:
1. Create an app at <https://developers.tiktok.com/> and add the
   **Content Posting API** product.
2. Request scopes: `video.upload` (drafts) and/or `video.publish`
   (direct post), plus `user.info.basic`.
3. In your TikTok app settings, add a **redirect URI** matching
   `TIKTOK_REDIRECT_URI` and verify the **URL prefix / domain** that your
   clips are served from (required for `PULL_FROM_URL` — this must be your
   `PUBLIC_BASE_URL` or your Vultr Object Storage domain).
4. Fill in `backend/.env`: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`,
   `TIKTOK_REDIRECT_URI`, `TIKTOK_SCOPES`.
5. Run the OAuth flow per account: `GET /api/tiktok/auth/url` → send the
   creator to that URL → TikTok calls `/api/tiktok/auth/callback` → you get
   an access/refresh token.

What you still need to build/decide (intentionally left as groundwork):
- **Token storage**: tokens are currently returned from the callback and
  passed into the publish call by hand (the Publish sheet has a temporary
  "access token" field). Persist tokens per TikTok account (DB / encrypted
  store) and look them up by account so creators don't paste tokens. See
  the `TODO(user)` notes in `tiktok.py` and `main.py`.
- **Multi-account UI**: a real account picker (the dashboard mock accounts
  in `frontend/lib/data.ts` are placeholders).
- **Publish status polling**: `TikTokClient.publish_status()` exists; wire
  it to show post results.

---

## 4. Store videos on a Vultr VPS + Object Storage (groundwork done)

### 4a. Object Storage for finished clips
Code: `backend/app/storage_backends/` (`local` and `vultr` backends,
selected by `STORAGE_BACKEND`). Vultr Object Storage is S3-compatible
(uses `boto3`).

To do:
1. In the Vultr panel, create an **Object Storage** subscription and a
   bucket.
2. Fill in `backend/.env`:
   - `STORAGE_BACKEND=vultr`
   - `VULTR_S3_ENDPOINT` (e.g. `https://ewr1.vultrobjects.com`)
   - `VULTR_S3_REGION`, `VULTR_S3_BUCKET`
   - `VULTR_S3_ACCESS_KEY`, `VULTR_S3_SECRET_KEY`
   - optional `VULTR_PUBLIC_BASE_URL` (CDN/custom domain)
3. `pip install boto3` (already in `requirements.txt`).

When enabled, finished clips are uploaded and the frontend/TikTok use the
public object URLs automatically. With `STORAGE_BACKEND=local`, clips are
served from disk via the API (and TikTok needs `PUBLIC_BASE_URL` set).

### 4b. The VPS itself
Provision a Vultr VPS (a few GB RAM + disk for VODs), install FFmpeg +
Python, and run the backend there (this is also your §2 backend host and
your §5 cloud worker).

---

## 5. Local vs cloud processing + worker microservice (groundwork done)

The Search page now has a **"Process locally / Process on cloud"** selector
(plumbed through `processing_mode` on the job). Jobs show a `local`/`cloud`
badge.

- **local**: the backend you call runs the whole pipeline in-process.
- **cloud**: the API host forwards the job to a remote **worker** (the same
  backend deployed on the Vultr VPS with `IS_WORKER=true`) via
  `backend/app/dispatch.py`. The worker does the heavy lifting and uploads
  clips to Vultr storage.

To do (only if you want the cloud option):
1. Deploy a second copy of the backend on the Vultr VPS with:
   - `IS_WORKER=true`
   - `STORAGE_BACKEND=vultr` (so clips land in shared storage)
   - a shared `WORKER_API_TOKEN`
2. On the API host (the one the frontend talks to), set:
   - `WORKER_URL` = the VPS worker's URL
   - `WORKER_API_TOKEN` = the same shared token
   - optionally `DEFAULT_PROCESSING_MODE=cloud`

What you may want to build later (the seam is intentionally small):
- Replace the direct HTTP hand-off with a real queue (Redis + RQ/Celery)
  for retries/scale.
- Mirror remote job status back to the API host (right now the cloud job's
  `remote_job_id` is stored in the job's `artifacts`; add polling/sync if
  you want full progress on the API host).

---

## 6. Quick checklist

- [ ] Vercel **Root Directory = `frontend`** + `BACKEND_URL` env var
- [ ] Backend hosted with HTTPS; `PUBLIC_BASE_URL` + `EXTRA_CORS_ORIGINS` set
- [ ] `OPENAI_API_KEY` set; FFmpeg installed
- [ ] TikTok app created; scopes + redirect URI + domain verified; keys in `.env`
- [ ] TikTok token storage per account implemented
- [ ] Vultr Object Storage bucket + `VULTR_S3_*` creds; `STORAGE_BACKEND=vultr`
- [ ] (optional) Vultr VPS worker with `IS_WORKER=true` + `WORKER_URL`/`WORKER_API_TOKEN`

---

## Where the new code lives

| Area | Files |
| --- | --- |
| Generate clips UI + polling | `frontend/components/search/kick-search.tsx`, `frontend/components/jobs/jobs-view.tsx`, `frontend/app/jobs/page.tsx`, `frontend/lib/api.ts` |
| Publish to TikTok | `backend/app/publish/tiktok.py`, `frontend/components/clips/publish-sheet.tsx`, `/api/tiktok/*` in `backend/app/main.py` |
| Vultr storage | `backend/app/storage_backends/` |
| Local/cloud processing + worker | `backend/app/dispatch.py`, `processing_mode` in `schemas.py`/`jobs.py` |
| Integration status UI | `frontend/components/studio/integrations.tsx`, `/api/config` |
| Vercel / env | `frontend/vercel.json`, `frontend/next.config.ts`, `*/.env.example` |
