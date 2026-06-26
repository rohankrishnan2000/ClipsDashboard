"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StreamerCard } from "@/components/clips/streamer-card";
import { streamers } from "@/lib/data";
import { ClapperboardIcon, FilmIcon } from "lucide-react";

const totalRaw = streamers.reduce((acc, s) => acc + s.rawVideos.length, 0);
const totalClips = streamers.reduce((acc, s) => acc + s.clips.length, 0);

function Grid({ mode }: { mode: "raw" | "clips" }) {
	return (
		<div className="grid grid-cols-1 gap-px bg-border p-px sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
			{streamers.map((s) => (
				<StreamerCard key={s.slug} mode={mode} streamer={s} />
			))}
		</div>
	);
}

export function ClipsTabs() {
	return (
		<Tabs defaultValue="unprocessed">
			<TabsList>
				<TabsTrigger value="unprocessed">
					<FilmIcon data-icon="inline-start" />
					Unprocessed
					<span className="ml-1.5 rounded bg-muted px-1.5 text-muted-foreground text-xs tabular-nums">
						{totalRaw}
					</span>
				</TabsTrigger>
				<TabsTrigger value="processed">
					<ClapperboardIcon data-icon="inline-start" />
					Processed
					<span className="ml-1.5 rounded bg-muted px-1.5 text-muted-foreground text-xs tabular-nums">
						{totalClips}
					</span>
				</TabsTrigger>
			</TabsList>
			<TabsContent value="unprocessed">
				<Grid mode="raw" />
			</TabsContent>
			<TabsContent value="processed">
				<Grid mode="clips" />
			</TabsContent>
		</Tabs>
	);
}
