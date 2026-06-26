import {
	CardContent,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Delta, DeltaIcon, DeltaValue } from "@/components/delta";
import { DashboardCard } from "@/components/dashboard-card";
import { tiktokAccounts } from "@/lib/data";
import { formatCompactNumber } from "@/components/formater";

function sum(selector: (a: (typeof tiktokAccounts)[number]) => number) {
	return tiktokAccounts.reduce((acc, a) => acc + selector(a), 0);
}

const totalViews = sum((a) => a.views);
const totalFollowers = sum((a) => a.followers);
const totalLikes = sum((a) => a.likes);
const avgEngagement =
	tiktokAccounts.reduce((acc, a) => acc + a.engagement, 0) /
	tiktokAccounts.length;

const stats = [
	{ label: "Total views", value: formatCompactNumber(totalViews), delta: 14.2 },
	{
		label: "Followers",
		value: formatCompactNumber(totalFollowers),
		delta: 9.6,
	},
	{ label: "Total likes", value: formatCompactNumber(totalLikes), delta: 11.3 },
	{
		label: "Avg engagement",
		value: `${avgEngagement.toFixed(1)}%`,
		delta: -1.2,
	},
] as const;

export function TikTokStats() {
	return (
		<>
			{stats.map((s) => (
				<DashboardCard key={s.label}>
					<CardHeader className="flex flex-row items-center justify-between">
						<CardTitle className="font-normal text-xs tracking-wide">
							{s.label}
						</CardTitle>
					</CardHeader>
					<CardContent className="flex flex-row items-center gap-2">
						<p className="font-semibold text-2xl tabular-nums">{s.value}</p>
					</CardContent>
					<CardFooter className="gap-1 rounded-none bg-background text-xs">
						<Delta value={s.delta}>
							<DeltaIcon />
							<DeltaValue />
						</Delta>
						<span className="text-muted-foreground">vs last week</span>
					</CardFooter>
				</DashboardCard>
			))}
		</>
	);
}
