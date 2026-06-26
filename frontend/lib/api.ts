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

export type CreateJobResponse = {
	job_id: string;
	status: JobStatus;
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
