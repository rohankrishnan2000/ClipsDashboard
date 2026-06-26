import Link from "next/link";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { CardContent, CardHeader } from "@/components/ui/card";
import { DashboardCard } from "@/components/dashboard-card";
import {
	formatDuration,
	totalClipDuration,
	totalRawDuration,
	type Streamer,
} from "@/lib/data";
import { ChevronRightIcon, ClapperboardIcon, FilmIcon } from "lucide-react";

export function StreamerCard({
	streamer,
	mode,
}: {
	streamer: Streamer;
	mode: "raw" | "clips";
}) {
	const count =
		mode === "raw" ? streamer.rawVideos.length : streamer.clips.length;
	const duration =
		mode === "raw"
			? totalRawDuration(streamer)
			: totalClipDuration(streamer);
	const Icon = mode === "raw" ? FilmIcon : ClapperboardIcon;
	const unit = mode === "raw" ? "videos" : "clips";

	return (
		<Link
			className="group block focus-visible:outline-none"
			href={`/clips/${streamer.slug}?tab=${mode === "raw" ? "videos" : "clips"}`}
		>
			<DashboardCard className="gap-0 transition-colors group-hover:bg-muted/40 group-focus-visible:ring-2 group-focus-visible:ring-ring">
				<div className="relative flex h-28 items-center justify-center overflow-hidden border-b bg-[radial-gradient(120%_120%_at_50%_0%,--theme(--color-foreground/.08),transparent)]">
					<Icon className="size-8 text-muted-foreground/60" />
					<Badge
						className="absolute top-2 right-2 tabular-nums"
						variant="secondary"
					>
						{count} {unit}
					</Badge>
				</div>
				<CardHeader className="gap-3">
					<div className="flex items-center gap-3">
						<Avatar className="size-9 rounded-md">
							<AvatarImage src={streamer.avatar} />
							<AvatarFallback>{streamer.name.charAt(0)}</AvatarFallback>
						</Avatar>
						<div className="flex min-w-0 flex-col">
							<span className="truncate font-medium text-sm">
								{streamer.name}
							</span>
							<span className="text-muted-foreground text-xs">
								{streamer.category}
							</span>
						</div>
						<ChevronRightIcon className="ml-auto size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
					</div>
				</CardHeader>
				<CardContent className="flex items-center justify-between text-muted-foreground text-xs">
					<span className="rounded bg-muted px-1.5 py-0.5 font-medium text-foreground/70">
						Kick
					</span>
					<span className="tabular-nums">
						{count > 0 ? formatDuration(duration) : "No footage yet"}
					</span>
				</CardContent>
			</DashboardCard>
		</Link>
	);
}
