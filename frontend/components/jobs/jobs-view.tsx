"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	Empty,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { DashboardCard } from "@/components/dashboard-card";
import { PublishSheet } from "@/components/clips/publish-sheet";
import {
	isActiveJob,
	jobStatusLabel,
	listJobs,
	type ClipCandidate,
	type JobRecord,
	type JobStatus,
} from "@/lib/api";
import {
	AlertCircleIcon,
	CloudIcon,
	DownloadIcon,
	LaptopIcon,
	ClapperboardIcon,
	SendIcon,
	SparklesIcon,
} from "lucide-react";

const POLL_MS = 2500;

const statusVariant: Record<JobStatus, "secondary" | "outline" | "default" | "destructive"> = {
	queued: "secondary",
	fetching_vods: "secondary",
	downloading: "secondary",
	extracting_audio: "secondary",
	transcribing: "secondary",
	analyzing: "secondary",
	cutting: "secondary",
	done: "default",
	failed: "destructive",
};

export function JobsView() {
	const [jobs, setJobs] = useState<JobRecord[] | null>(null);
	const [error, setError] = useState<string | null>(null);
	const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	const refresh = useCallback(async () => {
		try {
			const data = await listJobs();
			setJobs(data);
			setError(null);
			return data;
		} catch (err) {
			setError(
				err instanceof Error
					? err.message
					: "Could not reach the backend. Is it running?"
			);
			setJobs((prev) => prev ?? []);
			return [] as JobRecord[];
		}
	}, []);

	useEffect(() => {
		let cancelled = false;

		async function tick() {
			const data = await refresh();
			if (cancelled) {
				return;
			}
			const hasActive = data.some((j) => isActiveJob(j.status));
			if (hasActive) {
				timerRef.current = setTimeout(tick, POLL_MS);
			}
		}

		tick();
		return () => {
			cancelled = true;
			if (timerRef.current) {
				clearTimeout(timerRef.current);
			}
		};
	}, [refresh]);

	if (jobs === null) {
		return (
			<div className="flex flex-col gap-px bg-border">
				{Array.from({ length: 3 }).map((_, i) => (
					<DashboardCard className="gap-0" key={i}>
						<CardHeader className="gap-2">
							<Skeleton className="h-5 w-2/3" />
							<Skeleton className="h-4 w-full max-w-md" />
						</CardHeader>
					</DashboardCard>
				))}
			</div>
		);
	}

	return (
		<div className="flex flex-col gap-6">
			{error && (
				<Alert variant="destructive">
					<AlertCircleIcon />
					<AlertTitle>Backend unreachable</AlertTitle>
					<AlertDescription>{error}</AlertDescription>
				</Alert>
			)}

			{jobs.length === 0 ? (
				<Empty className="border bg-background py-16">
					<EmptyHeader>
						<EmptyMedia variant="icon">
							<ClapperboardIcon />
						</EmptyMedia>
						<EmptyTitle>No clipping jobs yet</EmptyTitle>
						<EmptyDescription>
							Head to Search, find a Kick VOD, and hit “Generate clips”.
						</EmptyDescription>
					</EmptyHeader>
				</Empty>
			) : (
				<div className="flex flex-col gap-px bg-border">
					{jobs.map((job) => (
						<JobCard job={job} key={job.job_id} />
					))}
				</div>
			)}
		</div>
	);
}

function JobCard({ job }: { job: JobRecord }) {
	const active = isActiveJob(job.status);
	const pct = Math.round((job.progress ?? 0) * 100);

	return (
		<DashboardCard className="gap-0">
			<CardHeader className="gap-2">
				<div className="flex flex-wrap items-center gap-2">
					<CardTitle className="min-w-0 flex-1 truncate text-base">
						{job.vod_title || "Untitled VOD"}
					</CardTitle>
					<Badge
						className="gap-1"
						variant={job.processing_mode === "cloud" ? "secondary" : "outline"}
					>
						{job.processing_mode === "cloud" ? (
							<CloudIcon className="size-3" />
						) : (
							<LaptopIcon className="size-3" />
						)}
						{job.processing_mode}
					</Badge>
					<Badge variant={statusVariant[job.status]}>
						{jobStatusLabel(job.status)}
					</Badge>
				</div>
				<p className="text-muted-foreground text-xs">
					Job {job.job_id} · {job.message}
				</p>
				{active && <Progress className="mt-1 max-w-xl" value={pct} />}
			</CardHeader>

			{job.status === "failed" && job.error && (
				<CardContent>
					<Alert variant="destructive">
						<AlertCircleIcon />
						<AlertTitle>Job failed</AlertTitle>
						<AlertDescription className="break-words">{job.error}</AlertDescription>
					</Alert>
				</CardContent>
			)}

			{job.results.length > 0 && (
				<CardContent className="grid grid-cols-1 gap-px bg-border p-0 sm:grid-cols-2 lg:grid-cols-3">
					{job.results.map((clip, i) => (
						<ClipCard clip={clip} jobId={job.job_id} key={`${job.job_id}-${i}`} />
					))}
				</CardContent>
			)}
		</DashboardCard>
	);
}

function ClipCard({ clip, jobId }: { clip: ClipCandidate; jobId: string }) {
	return (
		<div className="flex flex-col gap-3 bg-background p-4">
			<div className="relative aspect-video overflow-hidden rounded-md border bg-black">
				{clip.clip_url ? (
					<video
						className="size-full object-contain"
						controls
						preload="metadata"
						src={clip.clip_url}
					/>
				) : (
					<div className="flex size-full items-center justify-center">
						<ClapperboardIcon className="size-6 text-muted-foreground/50" />
					</div>
				)}
				<Badge
					className="absolute top-2 right-2 gap-1 tabular-nums"
					variant="secondary"
				>
					<SparklesIcon className="size-3" />
					{clip.score}
				</Badge>
			</div>
			<div className="flex flex-col gap-1">
				<p className="line-clamp-2 font-medium text-sm leading-snug">
					{clip.title}
				</p>
				<p className="line-clamp-2 text-muted-foreground text-xs">{clip.hook}</p>
				<div className="flex flex-wrap items-center gap-2 pt-1 text-muted-foreground text-xs">
					<Badge className="capitalize" variant="outline">
						{clip.clip_type}
					</Badge>
					<span className="tabular-nums">
						{clip.start_label} → {clip.end_label}
					</span>
				</div>
			</div>
			<div className="mt-auto flex gap-2">
				{clip.clip_url && (
					<Button asChild className="flex-1" size="sm" variant="outline">
						<a download href={clip.clip_url}>
							<DownloadIcon data-icon="inline-start" />
							Download
						</a>
					</Button>
				)}
				{clip.filename && (
					<PublishSheet
						target={{ jobId, filename: clip.filename, title: clip.title }}
						trigger={
							<Button className="flex-1" size="sm">
								<SendIcon data-icon="inline-start" />
								Publish
							</Button>
						}
					/>
				)}
			</div>
		</div>
	);
}
