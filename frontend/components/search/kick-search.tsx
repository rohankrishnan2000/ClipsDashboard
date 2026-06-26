"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import {
	Empty,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from "@/components/ui/empty";
import {
	InputGroup,
	InputGroupAddon,
	InputGroupButton,
	InputGroupInput,
} from "@/components/ui/input-group";
import {
	Select,
	SelectContent,
	SelectGroup,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { DashboardCard } from "@/components/dashboard-card";
import { formatDuration } from "@/lib/data";
import { createJob, searchKickVideos, type KickVideo } from "@/lib/api";
import {
	AlertCircleIcon,
	ClockIcon,
	SearchIcon,
	WandSparklesIcon,
} from "lucide-react";

type ClipState = "idle" | "queued" | "submitting";

function formatVodDate(value: string | null): string {
	if (!value) {
		return "Unknown date";
	}
	const date = new Date(value.replace(" ", "T"));
	if (Number.isNaN(date.getTime())) {
		return value;
	}
	return date.toLocaleDateString("en-US", {
		day: "numeric",
		month: "short",
		year: "numeric",
	});
}

export function KickSearch() {
	const [query, setQuery] = useState("");
	const [months, setMonths] = useState("3");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [hasSearched, setHasSearched] = useState(false);
	const [username, setUsername] = useState("");
	const [videos, setVideos] = useState<KickVideo[]>([]);
	const [clipStates, setClipStates] = useState<Record<string, ClipState>>({});
	const abortRef = useRef<AbortController | null>(null);

	async function runSearch(e?: React.FormEvent) {
		e?.preventDefault();
		const trimmed = query.trim();
		if (!trimmed) {
			setError("Enter a Kick streamer username to search.");
			return;
		}

		abortRef.current?.abort();
		const controller = new AbortController();
		abortRef.current = controller;

		setLoading(true);
		setError(null);
		setHasSearched(true);

		try {
			const data = await searchKickVideos(
				trimmed,
				Number(months),
				controller.signal
			);
			setUsername(data.username);
			setVideos(data.videos);
		} catch (err) {
			if ((err as Error).name === "AbortError") {
				return;
			}
			setVideos([]);
			setError(
				err instanceof Error
					? err.message
					: "Something went wrong while searching Kick."
			);
		} finally {
			if (abortRef.current === controller) {
				setLoading(false);
			}
		}
	}

	async function generateClips(video: KickVideo) {
		if (clipStates[video.id] === "submitting") {
			return;
		}
		setClipStates((s) => ({ ...s, [video.id]: "submitting" }));
		try {
			const job = await createJob({
				vod_url: video.url,
				vod_title: video.title,
			});
			setClipStates((s) => ({ ...s, [video.id]: "queued" }));
			toast.success("Clipping job queued", {
				description: `Job ${job.job_id.slice(0, 8)} — ${video.title.slice(0, 48)}`,
			});
		} catch (err) {
			setClipStates((s) => ({ ...s, [video.id]: "idle" }));
			toast.error("Could not queue job", {
				description:
					err instanceof Error ? err.message : "Unknown error from backend.",
			});
		}
	}

	return (
		<div className="flex flex-col gap-6">
			<form className="flex flex-col gap-3 sm:flex-row" onSubmit={runSearch}>
				<InputGroup className="h-9 flex-1">
					<InputGroupInput
						onChange={(e) => setQuery(e.target.value)}
						placeholder="Search a Kick streamer (e.g. xqc, trainwreckstv)…"
						value={query}
					/>
					<InputGroupAddon>
						<SearchIcon />
					</InputGroupAddon>
					<InputGroupAddon align="inline-end">
						<InputGroupButton disabled={loading} type="submit">
							{loading ? <Spinner /> : "Search"}
						</InputGroupButton>
					</InputGroupAddon>
				</InputGroup>
				<Select onValueChange={setMonths} value={months}>
					<SelectTrigger className="sm:w-44">
						<SelectValue placeholder="Lookback" />
					</SelectTrigger>
					<SelectContent>
						<SelectGroup>
							<SelectItem value="1">Last month</SelectItem>
							<SelectItem value="3">Last 3 months</SelectItem>
							<SelectItem value="6">Last 6 months</SelectItem>
							<SelectItem value="12">Last 12 months</SelectItem>
						</SelectGroup>
					</SelectContent>
				</Select>
			</form>

			{error && (
				<Alert variant="destructive">
					<AlertCircleIcon />
					<AlertTitle>Search failed</AlertTitle>
					<AlertDescription>{error}</AlertDescription>
				</Alert>
			)}

			{loading && (
				<div className="grid grid-cols-1 gap-px bg-border p-px md:grid-cols-2 xl:grid-cols-3">
					{Array.from({ length: 6 }).map((_, i) => (
						<DashboardCard className="gap-0" key={i}>
							<Skeleton className="h-36 w-full rounded-none" />
							<CardHeader className="gap-2">
								<Skeleton className="h-4 w-3/4" />
								<Skeleton className="h-4 w-1/2" />
							</CardHeader>
							<CardFooter>
								<Skeleton className="h-9 w-full" />
							</CardFooter>
						</DashboardCard>
					))}
				</div>
			)}

			{!loading && !error && !hasSearched && (
				<Empty className="border bg-background py-16">
					<EmptyHeader>
						<EmptyMedia variant="icon">
							<SearchIcon />
						</EmptyMedia>
						<EmptyTitle>Search Kick for a streamer</EmptyTitle>
						<EmptyDescription>
							Type a streamer&apos;s Kick username to pull their recent VODs,
							then send one off to be cut into clips.
						</EmptyDescription>
					</EmptyHeader>
				</Empty>
			)}

			{!loading && !error && hasSearched && videos.length === 0 && (
				<Empty className="border bg-background py-16">
					<EmptyHeader>
						<EmptyMedia variant="icon">
							<SearchIcon />
						</EmptyMedia>
						<EmptyTitle>
							No VODs found for &ldquo;{query.trim()}&rdquo;
						</EmptyTitle>
						<EmptyDescription>
							Check the spelling, or widen the lookback window.
						</EmptyDescription>
					</EmptyHeader>
				</Empty>
			)}

			{!loading && videos.length > 0 && (
				<div className="grid grid-cols-1 gap-px bg-border p-px md:grid-cols-2 xl:grid-cols-3">
					{videos.map((v) => {
						const state = clipStates[v.id] ?? "idle";
						return (
							<DashboardCard className="gap-0" key={v.id}>
								<div className="relative aspect-video w-full overflow-hidden border-b bg-muted">
									{v.thumbnail_url ? (
										// eslint-disable-next-line @next/next/no-img-element
										<img
											alt={v.title}
											className="size-full object-cover"
											loading="lazy"
											src={v.thumbnail_url}
										/>
									) : (
										<div className="flex size-full items-center justify-center bg-[radial-gradient(120%_120%_at_50%_0%,--theme(--color-foreground/.08),transparent)]">
											<SearchIcon className="size-7 text-muted-foreground/50" />
										</div>
									)}
									{v.duration_sec != null && (
										<Badge
											className="absolute right-2 bottom-2 gap-1 tabular-nums"
											variant="secondary"
										>
											<ClockIcon className="size-3" />
											{formatDuration(v.duration_sec)}
										</Badge>
									)}
								</div>
								<CardHeader className="gap-3">
									<div className="flex items-center gap-3">
										<Avatar className="size-8 rounded-md">
											<AvatarFallback>
												{username.charAt(0).toUpperCase()}
											</AvatarFallback>
										</Avatar>
										<div className="flex min-w-0 flex-col">
											<span className="font-medium text-sm">{username}</span>
											<span className="text-muted-foreground text-xs">
												{formatVodDate(v.created_at)}
											</span>
										</div>
										<Badge className="ml-auto" variant="outline">
											Kick
										</Badge>
									</div>
									<p className="line-clamp-2 font-medium text-sm leading-snug">
										{v.title}
									</p>
								</CardHeader>
								<CardContent />
								<CardFooter>
									<Button
										className="w-full"
										disabled={state !== "idle"}
										onClick={() => generateClips(v)}
										variant={state === "queued" ? "outline" : "default"}
									>
										{state === "submitting" ? (
											<>
												<Spinner data-icon="inline-start" />
												Queuing…
											</>
										) : state === "queued" ? (
											"Queued for clipping"
										) : (
											<>
												<WandSparklesIcon data-icon="inline-start" />
												Generate clips
											</>
										)}
									</Button>
								</CardFooter>
							</DashboardCard>
						);
					})}
				</div>
			)}
		</div>
	);
}
