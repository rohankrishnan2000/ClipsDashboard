// Mock data layer for the ClipForge clipping-bot dashboard.
// Swap these out for real API calls when wiring up the backend.

export type TikTokAccount = {
	handle: string;
	niche: string;
	avatar: string;
	followers: number;
	views: number;
	likes: number;
	posts: number;
	engagement: number; // percent
	delta: number; // percent change vs last week
};

export type ViewsPoint = {
	date: string; // ISO
	views: number;
};

export type TopClip = {
	id: string;
	title: string;
	streamer: string;
	account: string;
	views: number;
	delta: number;
};

export type ClipStatus = "ready" | "scheduled" | "posted";
export type ProcessingStatus = "idle" | "queued" | "processing" | "done";

export type RawVideo = {
	id: string;
	title: string;
	durationSec: number;
	recordedAt: string; // ISO
	sizeGb: number;
	status: ProcessingStatus;
	progress?: number; // 0-100 when processing
	clipsFound?: number;
};

export type Clip = {
	id: string;
	title: string;
	durationSec: number;
	createdAt: string; // ISO
	score: number; // virality score 0-100
	status: ClipStatus;
	sourceVideo: string;
};

export type Streamer = {
	slug: string;
	name: string;
	platform: "kick";
	avatar: string;
	category: string;
	rawVideos: RawVideo[];
	clips: Clip[];
};

export type KickResult = {
	id: string;
	streamer: string;
	avatar: string;
	title: string;
	category: string;
	durationSec: number;
	streamedAt: string; // ISO
	viewers: number;
	sizeGb: number;
};

// ── TikTok performance ────────────────────────────────────────────────

export const tiktokAccounts: TikTokAccount[] = [
	{
		handle: "@clipforge.gaming",
		niche: "Gaming",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=gaming",
		followers: 184_200,
		views: 4_820_000,
		likes: 612_400,
		posts: 142,
		engagement: 9.4,
		delta: 12.8,
	},
	{
		handle: "@clipforge.irl",
		niche: "IRL / Vlog",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=irl",
		followers: 96_700,
		views: 2_310_000,
		likes: 288_900,
		posts: 118,
		engagement: 7.1,
		delta: 5.2,
	},
	{
		handle: "@clipforge.rage",
		niche: "Rage Clips",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=rage",
		followers: 241_500,
		views: 7_940_000,
		likes: 1_120_000,
		posts: 203,
		engagement: 11.2,
		delta: 18.6,
	},
	{
		handle: "@clipforge.funny",
		niche: "Funny Moments",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=funny",
		followers: 58_300,
		views: 1_180_000,
		likes: 142_700,
		posts: 87,
		engagement: 6.3,
		delta: -2.4,
	},
];

export const viewsTrend: ViewsPoint[] = [
	{ date: "2026-06-19", views: 412_000 },
	{ date: "2026-06-20", views: 388_000 },
	{ date: "2026-06-21", views: 521_000 },
	{ date: "2026-06-22", views: 604_000 },
	{ date: "2026-06-23", views: 712_000 },
	{ date: "2026-06-24", views: 689_000 },
	{ date: "2026-06-25", views: 834_000 },
];

export const topClips: TopClip[] = [
	{
		id: "tc1",
		title: "INSANE 1v5 clutch goes viral",
		streamer: "xQc",
		account: "@clipforge.gaming",
		views: 1_240_000,
		delta: 34.1,
	},
	{
		id: "tc2",
		title: "Streamer rage quits live on stream",
		streamer: "Trainwreck",
		account: "@clipforge.rage",
		views: 982_000,
		delta: 21.7,
	},
	{
		id: "tc3",
		title: "He didn't expect THAT to happen",
		streamer: "Adin Ross",
		account: "@clipforge.funny",
		views: 740_500,
		delta: 12.3,
	},
	{
		id: "tc4",
		title: "Chat cooks the streamer",
		streamer: "Amouranth",
		account: "@clipforge.irl",
		views: 511_200,
		delta: -4.8,
	},
];

// ── Streamers, raw footage & clips ────────────────────────────────────

export const streamers: Streamer[] = [
	{
		slug: "xqc",
		name: "xQc",
		platform: "kick",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=xqc",
		category: "Just Chatting",
		rawVideos: [
			{
				id: "xqc-v1",
				title: "Reacting to drama + GTA RP",
				durationSec: 21_840,
				recordedAt: "2026-06-24",
				sizeGb: 14.2,
				status: "done",
				clipsFound: 12,
			},
			{
				id: "xqc-v2",
				title: "Marathon variety stream",
				durationSec: 33_120,
				recordedAt: "2026-06-22",
				sizeGb: 22.8,
				status: "processing",
				progress: 64,
			},
			{
				id: "xqc-v3",
				title: "Subathon day 3",
				durationSec: 28_500,
				recordedAt: "2026-06-20",
				sizeGb: 19.1,
				status: "idle",
			},
		],
		clips: [
			{
				id: "xqc-c1",
				title: "INSANE 1v5 clutch goes viral",
				durationSec: 38,
				createdAt: "2026-06-24",
				score: 94,
				status: "posted",
				sourceVideo: "xqc-v1",
			},
			{
				id: "xqc-c2",
				title: "He reads the worst donation ever",
				durationSec: 52,
				createdAt: "2026-06-24",
				score: 88,
				status: "scheduled",
				sourceVideo: "xqc-v1",
			},
			{
				id: "xqc-c3",
				title: "Juicer moment of the night",
				durationSec: 27,
				createdAt: "2026-06-24",
				score: 81,
				status: "ready",
				sourceVideo: "xqc-v1",
			},
		],
	},
	{
		slug: "trainwreck",
		name: "Trainwreck",
		platform: "kick",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=train",
		category: "Slots & Casino",
		rawVideos: [
			{
				id: "tw-v1",
				title: "Late night slots session",
				durationSec: 25_200,
				recordedAt: "2026-06-23",
				sizeGb: 16.4,
				status: "done",
				clipsFound: 8,
			},
			{
				id: "tw-v2",
				title: "Big bonus hunt",
				durationSec: 18_900,
				recordedAt: "2026-06-21",
				sizeGb: 12.0,
				status: "idle",
			},
		],
		clips: [
			{
				id: "tw-c1",
				title: "Streamer rage quits live on stream",
				durationSec: 44,
				createdAt: "2026-06-23",
				score: 91,
				status: "posted",
				sourceVideo: "tw-v1",
			},
			{
				id: "tw-c2",
				title: "Biggest win of the year",
				durationSec: 61,
				createdAt: "2026-06-23",
				score: 86,
				status: "ready",
				sourceVideo: "tw-v1",
			},
		],
	},
	{
		slug: "adin-ross",
		name: "Adin Ross",
		platform: "kick",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=adin",
		category: "Just Chatting",
		rawVideos: [
			{
				id: "ar-v1",
				title: "Celebrity guest interview",
				durationSec: 14_400,
				recordedAt: "2026-06-25",
				sizeGb: 9.8,
				status: "queued",
			},
			{
				id: "ar-v2",
				title: "Watch party + reactions",
				durationSec: 20_700,
				recordedAt: "2026-06-22",
				sizeGb: 13.6,
				status: "done",
				clipsFound: 6,
			},
		],
		clips: [
			{
				id: "ar-c1",
				title: "He didn't expect THAT to happen",
				durationSec: 33,
				createdAt: "2026-06-22",
				score: 89,
				status: "posted",
				sourceVideo: "ar-v2",
			},
		],
	},
	{
		slug: "amouranth",
		name: "Amouranth",
		platform: "kick",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=amo",
		category: "IRL",
		rawVideos: [
			{
				id: "am-v1",
				title: "IRL outdoor adventure",
				durationSec: 16_200,
				recordedAt: "2026-06-24",
				sizeGb: 11.2,
				status: "idle",
			},
		],
		clips: [
			{
				id: "am-c1",
				title: "Chat cooks the streamer",
				durationSec: 41,
				createdAt: "2026-06-24",
				score: 78,
				status: "ready",
				sourceVideo: "am-v1",
			},
			{
				id: "am-c2",
				title: "Unexpected guest appearance",
				durationSec: 29,
				createdAt: "2026-06-24",
				score: 72,
				status: "scheduled",
				sourceVideo: "am-v1",
			},
		],
	},
	{
		slug: "nickmercs",
		name: "Nickmercs",
		platform: "kick",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=nick",
		category: "FPS",
		rawVideos: [
			{
				id: "nm-v1",
				title: "Ranked grind to top 500",
				durationSec: 23_400,
				recordedAt: "2026-06-23",
				sizeGb: 15.0,
				status: "done",
				clipsFound: 9,
			},
		],
		clips: [
			{
				id: "nm-c1",
				title: "Cracked 30 bomb highlight",
				durationSec: 36,
				createdAt: "2026-06-23",
				score: 84,
				status: "ready",
				sourceVideo: "nm-v1",
			},
		],
	},
	{
		slug: "ice-poseidon",
		name: "Ice Poseidon",
		platform: "kick",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=ice",
		category: "IRL",
		rawVideos: [
			{
				id: "ip-v1",
				title: "City walk gone wrong",
				durationSec: 19_800,
				recordedAt: "2026-06-21",
				sizeGb: 12.9,
				status: "idle",
			},
		],
		clips: [],
	},
];

// ── Kick search results ───────────────────────────────────────────────

export const kickResults: KickResult[] = [
	{
		id: "k1",
		streamer: "xQc",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=xqc",
		title: "REACTING TO EVERYTHING + GTA RP LATER",
		category: "Just Chatting",
		durationSec: 21_840,
		streamedAt: "2026-06-24",
		viewers: 64_200,
		sizeGb: 14.2,
	},
	{
		id: "k2",
		streamer: "Trainwreck",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=train",
		title: "LATE NIGHT SLOTS — BONUS HUNT OPENING",
		category: "Slots & Casino",
		durationSec: 25_200,
		streamedAt: "2026-06-23",
		viewers: 38_500,
		sizeGb: 16.4,
	},
	{
		id: "k3",
		streamer: "Adin Ross",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=adin",
		title: "BIG GUEST TONIGHT 👀",
		category: "Just Chatting",
		durationSec: 14_400,
		streamedAt: "2026-06-25",
		viewers: 92_100,
		sizeGb: 9.8,
	},
	{
		id: "k4",
		streamer: "Nickmercs",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=nick",
		title: "RANKED GRIND — ROAD TO TOP 500",
		category: "FPS",
		durationSec: 23_400,
		streamedAt: "2026-06-23",
		viewers: 27_800,
		sizeGb: 15.0,
	},
	{
		id: "k5",
		streamer: "Amouranth",
		avatar: "https://api.dicebear.com/9.x/glass/svg?seed=amo",
		title: "IRL ADVENTURE DAY — COME ALONG",
		category: "IRL",
		durationSec: 16_200,
		streamedAt: "2026-06-24",
		viewers: 19_400,
		sizeGb: 11.2,
	},
];

// ── Helpers ───────────────────────────────────────────────────────────

export function getStreamer(slug: string): Streamer | undefined {
	return streamers.find((s) => s.slug === slug);
}

export function formatDuration(totalSeconds: number): string {
	const h = Math.floor(totalSeconds / 3600);
	const m = Math.floor((totalSeconds % 3600) / 60);
	const s = totalSeconds % 60;
	if (h > 0) {
		return `${h}h ${m}m`;
	}
	if (m > 0) {
		return `${m}m ${s.toString().padStart(2, "0")}s`;
	}
	return `${s}s`;
}

export function totalRawDuration(s: Streamer): number {
	return s.rawVideos.reduce((acc, v) => acc + v.durationSec, 0);
}

export function totalClipDuration(s: Streamer): number {
	return s.clips.reduce((acc, c) => acc + c.durationSec, 0);
}
