"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import {
	Empty,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DashboardCard } from "@/components/dashboard-card";
import { formatDate } from "@/components/formater";
import {
	formatDuration,
	type Clip,
	type ProcessingStatus,
	type RawVideo,
	type Streamer,
} from "@/lib/data";
import {
	ClapperboardIcon,
	FilmIcon,
	HardDriveIcon,
	SparklesIcon,
	WandSparklesIcon,
} from "lucide-react";

type VideoUiState = {
	status: ProcessingStatus;
	progress: number;
	clipsFound: number;
};

const statusBadge: Record<
	ProcessingStatus,
	{ label: string; variant: "secondary" | "outline" | "default" }
> = {
	idle: { label: "Not processed", variant: "outline" },
	queued: { label: "Queued", variant: "secondary" },
	processing: { label: "Processing", variant: "secondary" },
	done: { label: "Processed", variant: "default" },
};

const clipStatusVariant: Record<Clip["status"], "secondary" | "outline" | "default"> =
	{
		ready: "outline",
		scheduled: "secondary",
		posted: "default",
	};

export function StreamerDetail({
	streamer,
	initialTab,
}: {
	streamer: Streamer;
	initialTab: "videos" | "clips";
}) {
	const [videos, setVideos] = useState<Record<string, VideoUiState>>(() =>
		Object.fromEntries(
			streamer.rawVideos.map((v) => [
				v.id,
				{ status: v.status, progress: v.progress ?? 0, clipsFound: v.clipsFound ?? 0 },
			])
		)
	);

	function processVideo(video: RawVideo) {
		const current = videos[video.id];
		if (current.status === "processing" || current.status === "queued") {
			return;
		}
		setVideos((s) => ({
			...s,
			[video.id]: { status: "processing", progress: 0, clipsFound: 0 },
		}));
		toast.info(`Sending "${video.title}" for processing…`);

		const interval = setInterval(() => {
			setVideos((s) => {
				const v = s[video.id];
				if (!v) {
					return s;
				}
				const next = Math.min(v.progress + 10, 100);
				if (next >= 100) {
					clearInterval(interval);
					const found = 5 + Math.floor(Math.random() * 8);
					toast.success(`Found ${found} clips in "${video.title}".`);
					return {
						...s,
						[video.id]: { status: "done", progress: 100, clipsFound: found },
					};
				}
				return { ...s, [video.id]: { ...v, status: "processing", progress: next } };
			});
		}, 320);
	}

	return (
		<div className="flex flex-col gap-6">
			{/* Streamer header */}
			<DashboardCard className="gap-0">
				<CardHeader className="flex flex-row flex-wrap items-center gap-4">
					<Avatar className="size-14 rounded-lg">
						<AvatarImage src={streamer.avatar} />
						<AvatarFallback>{streamer.name.charAt(0)}</AvatarFallback>
					</Avatar>
					<div className="flex flex-col gap-1">
						<div className="flex items-center gap-2">
							<CardTitle className="text-xl">{streamer.name}</CardTitle>
							<Badge variant="secondary">Kick</Badge>
						</div>
						<CardDescription>{streamer.category}</CardDescription>
					</div>
					<div className="ml-auto flex gap-6 text-sm">
						<div className="flex flex-col">
							<span className="font-semibold text-lg tabular-nums">
								{streamer.rawVideos.length}
							</span>
							<span className="text-muted-foreground text-xs">Full videos</span>
						</div>
						<div className="flex flex-col">
							<span className="font-semibold text-lg tabular-nums">
								{streamer.clips.length}
							</span>
							<span className="text-muted-foreground text-xs">Clips</span>
						</div>
					</div>
				</CardHeader>
			</DashboardCard>

			<Tabs defaultValue={initialTab}>
				<TabsList>
					<TabsTrigger value="videos">
						<FilmIcon data-icon="inline-start" />
						Full videos
					</TabsTrigger>
					<TabsTrigger value="clips">
						<ClapperboardIcon data-icon="inline-start" />
						Clips
					</TabsTrigger>
				</TabsList>

				{/* Full videos — send for processing */}
				<TabsContent className="flex flex-col gap-px bg-border" value="videos">
					{streamer.rawVideos.length === 0 ? (
						<EmptyFootage />
					) : (
						streamer.rawVideos.map((v) => {
							const ui = videos[v.id];
							const badge = statusBadge[ui.status];
							return (
								<DashboardCard className="gap-0" key={v.id}>
									<CardContent className="flex flex-col gap-3 py-4 md:flex-row md:items-center">
										<div className="flex min-w-0 flex-1 flex-col gap-1">
											<div className="flex items-center gap-2">
												<span className="truncate font-medium">{v.title}</span>
												<Badge variant={badge.variant}>
													{ui.status === "done"
														? `Processed · ${ui.clipsFound} clips`
														: badge.label}
												</Badge>
											</div>
											<div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground text-xs">
												<span className="tabular-nums">
													{formatDuration(v.durationSec)}
												</span>
												<span>{formatDate(v.recordedAt, "full")}</span>
												<span className="inline-flex items-center gap-1 tabular-nums">
													<HardDriveIcon className="size-3.5" />
													{v.sizeGb.toFixed(1)} GB
												</span>
											</div>
											{ui.status === "processing" && (
												<Progress className="mt-1 max-w-md" value={ui.progress} />
											)}
										</div>
										<div className="md:w-52">
											<Button
												className="w-full"
												disabled={
													ui.status === "processing" || ui.status === "queued"
												}
												onClick={() => processVideo(v)}
												variant={ui.status === "done" ? "outline" : "default"}
											>
												<WandSparklesIcon data-icon="inline-start" />
												{ui.status === "processing"
													? `Processing… ${ui.progress}%`
													: ui.status === "queued"
														? "Queued"
														: ui.status === "done"
															? "Re-process"
															: "Send for processing"}
											</Button>
										</div>
									</CardContent>
								</DashboardCard>
							);
						})
					)}
				</TabsContent>

				{/* Generated clips */}
				<TabsContent
					className="grid grid-cols-1 gap-px bg-border md:grid-cols-2 lg:grid-cols-3"
					value="clips"
				>
					{streamer.clips.length === 0 ? (
						<div className="md:col-span-2 lg:col-span-3">
							<NoClips />
						</div>
					) : (
						streamer.clips.map((c) => (
							<DashboardCard className="gap-0" key={c.id}>
								<div className="relative flex h-24 items-center justify-center border-b bg-[radial-gradient(120%_120%_at_50%_0%,--theme(--color-foreground/.08),transparent)]">
									<ClapperboardIcon className="size-7 text-muted-foreground/60" />
									<Badge
										className="absolute top-2 right-2 gap-1 tabular-nums"
										variant="secondary"
									>
										<SparklesIcon className="size-3" />
										{c.score}
									</Badge>
								</div>
								<CardHeader className="gap-2">
									<p className="line-clamp-2 font-medium text-sm leading-snug">
										{c.title}
									</p>
								</CardHeader>
								<CardContent className="flex items-center justify-between text-muted-foreground text-xs">
									<span className="tabular-nums">
										{formatDuration(c.durationSec)}
									</span>
									<Badge
										className="capitalize"
										variant={clipStatusVariant[c.status]}
									>
										{c.status}
									</Badge>
								</CardContent>
							</DashboardCard>
						))
					)}
				</TabsContent>
			</Tabs>
		</div>
	);
}

function EmptyFootage() {
	return (
		<Empty className="border bg-background">
			<EmptyHeader>
				<EmptyMedia variant="icon">
					<FilmIcon />
				</EmptyMedia>
				<EmptyTitle>No footage yet</EmptyTitle>
				<EmptyDescription>
					Download a stream from the Search tab to get started.
				</EmptyDescription>
			</EmptyHeader>
		</Empty>
	);
}

function NoClips() {
	return (
		<Empty className="border bg-background">
			<EmptyHeader>
				<EmptyMedia variant="icon">
					<ClapperboardIcon />
				</EmptyMedia>
				<EmptyTitle>No clips yet</EmptyTitle>
				<EmptyDescription>
					Send a full video for processing to generate clips.
				</EmptyDescription>
			</EmptyHeader>
		</Empty>
	);
}
