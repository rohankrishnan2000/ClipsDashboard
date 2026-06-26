// Typed client for the FastAPI clipping-bot backend.
// Requests go to /api/* and are proxied to the backend (see next.config.ts).

export type KickVideo = {
	id: string;
	title: string;
	url: string;
	created_at: string | null;
	duration_sec: number | null;
	thumbnail_url: string | null;
};

export type KickVideosResponse = {
	username: string;
	videos: KickVideo[];
};

export type JobStatus =
	| "queued"
	| "fetching_vods"
	| "downloading"
	| "extracting_audio"
	| "transcribing"
	| "analyzing"
	| "cutting"
	| "done"
	| "failed";

export type ProcessingMode = "local" | "cloud";

export type CreateJobResponse = {
	job_id: string;
	status: JobStatus;
};

export type ClipCandidate = {
	start_time: number;
	end_time: number;
	start_label: string;
	end_label: string;
	title: string;
	hook: string;
	reason: string;
	score: number;
	clip_type: string;
	filename: string | null;
	clip_url: string | null;
};

export type JobRecord = {
	job_id: string;
	status: JobStatus;
	progress: number;
	message: string;
	vod_url: string;
	vod_title: string;
	clip_count: number;
	processing_mode: ProcessingMode;
	created_at: string;
	updated_at: string;
	error: string | null;
	results: ClipCandidate[];
	artifacts: Record<string, unknown>;
};

export type AppConfig = {
	openai_configured: boolean;
	tiktok_configured: boolean;
	vultr_configured: boolean;
	worker_configured: boolean;
	default_processing_mode: ProcessingMode;
	storage_backend: string;
};

export type TikTokPublishResponse = {
	publish_id: string;
	status: string;
	mode: string;
};

async function parseError(res: Response): Promise<string> {
	try {
		const body = await res.json();
		if (body?.detail) {
			return typeof body.detail === "string"
				? body.detail
				: JSON.stringify(body.detail);
		}
	} catch {
		// fall through
	}
	return `Request failed (${res.status})`;
}

/** Look up a Kick channel's recent VODs by username. */
export async function searchKickVideos(
	username: string,
	months: number,
	signal?: AbortSignal
): Promise<KickVideosResponse> {
	const params = new URLSearchParams({
		username: username.trim().replace(/^@/, ""),
		months: String(months),
	});
	const res = await fetch(`/api/kick/videos?${params.toString()}`, { signal });
	if (!res.ok) {
		throw new Error(await parseError(res));
	}
	return (await res.json()) as KickVideosResponse;
}

/** Queue a clipping job for a VOD. */
export async function createJob(input: {
	vod_url: string;
	vod_title: string;
	clip_count?: number;
	processing_mode?: ProcessingMode;
}): Promise<CreateJobResponse> {
	const res = await fetch("/api/jobs", {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify({ clip_count: 5, ...input }),
	});
	if (!res.ok) {
		throw new Error(await parseError(res));
	}
	return (await res.json()) as CreateJobResponse;
}

/** List all known clipping jobs (most recent first). */
export async function listJobs(signal?: AbortSignal): Promise<JobRecord[]> {
	const res = await fetch("/api/jobs", { signal });
	if (!res.ok) {
		throw new Error(await parseError(res));
	}
	const body = (await res.json()) as { jobs: JobRecord[] };
	return body.jobs;
}

/** Fetch a single job's current state (for progress polling). */
export async function getJob(
	jobId: string,
	signal?: AbortSignal
): Promise<JobRecord> {
	const res = await fetch(`/api/jobs/${jobId}`, { signal });
	if (!res.ok) {
		throw new Error(await parseError(res));
	}
	return (await res.json()) as JobRecord;
}

/** Which integrations (OpenAI, TikTok, Vultr, worker) are configured. */
export async function getConfig(signal?: AbortSignal): Promise<AppConfig> {
	const res = await fetch("/api/config", { signal });
	if (!res.ok) {
		throw new Error(await parseError(res));
	}
	return (await res.json()) as AppConfig;
}

/** Publish a generated clip to TikTok (direct post or upload to drafts). */
export async function publishToTikTok(input: {
	job_id: string;
	filename: string;
	access_token: string;
	account?: string;
	caption?: string;
	mode?: "direct" | "draft";
	privacy_level?:
		| "PUBLIC_TO_EVERYONE"
		| "MUTUAL_FOLLOW_FRIENDS"
		| "FOLLOWER_OF_CREATOR"
		| "SELF_ONLY";
}): Promise<TikTokPublishResponse> {
	const res = await fetch("/api/tiktok/publish", {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify(input),
	});
	if (!res.ok) {
		throw new Error(await parseError(res));
	}
	return (await res.json()) as TikTokPublishResponse;
}

/** True while a job is still being worked on. */
export function isActiveJob(status: JobStatus): boolean {
	return status !== "done" && status !== "failed";
}

const JOB_STATUS_LABELS: Record<JobStatus, string> = {
	queued: "Queued",
	fetching_vods: "Fetching VODs",
	downloading: "Downloading VOD",
	extracting_audio: "Extracting audio",
	transcribing: "Transcribing",
	analyzing: "Finding clips",
	cutting: "Cutting clips",
	done: "Done",
	failed: "Failed",
};

export function jobStatusLabel(status: JobStatus): string {
	return JOB_STATUS_LABELS[status] ?? status;
}
