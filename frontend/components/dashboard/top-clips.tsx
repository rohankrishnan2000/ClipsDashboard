import {
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Delta, DeltaIcon, DeltaValue } from "@/components/delta";
import { DashboardCard } from "@/components/dashboard-card";
import { topClips } from "@/lib/data";
import { formatCompactNumber } from "@/components/formater";

export function TopClips() {
	return (
		<DashboardCard className="gap-0 md:col-span-2">
			<CardHeader className="border-b">
				<CardTitle className="text-base">Top performing clips</CardTitle>
				<CardDescription>Your best clips this week, ranked by views.</CardDescription>
			</CardHeader>
			<CardContent className="flex flex-col divide-y p-0">
				{topClips.map((clip, i) => (
					<div className="flex items-center gap-4 px-6 py-3" key={clip.id}>
						<span className="w-4 font-mono text-muted-foreground text-sm tabular-nums">
							{i + 1}
						</span>
						<div className="flex min-w-0 flex-1 flex-col">
							<span className="truncate font-medium text-sm">{clip.title}</span>
							<span className="text-muted-foreground text-xs">
								{clip.streamer} · {clip.account}
							</span>
						</div>
						<div className="flex flex-col items-end gap-1">
							<span className="font-medium text-sm tabular-nums">
								{formatCompactNumber(clip.views)}
							</span>
							<Delta value={clip.delta} variant="badge">
								<DeltaIcon variant="trend" />
								<DeltaValue />
							</Delta>
						</div>
					</div>
				))}
			</CardContent>
		</DashboardCard>
	);
}
