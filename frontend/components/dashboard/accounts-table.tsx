import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { Delta, DeltaIcon, DeltaValue } from "@/components/delta";
import { DashboardCard } from "@/components/dashboard-card";
import { tiktokAccounts } from "@/lib/data";
import { formatCompactNumber } from "@/components/formater";

export function AccountsTable() {
	return (
		<DashboardCard className="gap-0 md:col-span-4">
			<CardHeader className="border-b">
				<CardTitle className="text-base">Account performance</CardTitle>
				<CardDescription>
					Per-account reach and engagement across your TikTok network.
				</CardDescription>
			</CardHeader>
			<Table>
				<TableHeader>
					<TableRow>
						<TableHead className="ps-6">Account</TableHead>
						<TableHead className="text-right tabular-nums">Followers</TableHead>
						<TableHead className="text-right tabular-nums">Views</TableHead>
						<TableHead className="text-right tabular-nums">Likes</TableHead>
						<TableHead className="text-right tabular-nums">Posts</TableHead>
						<TableHead className="text-right tabular-nums">Engmt.</TableHead>
						<TableHead className="pe-6 text-right tabular-nums">Trend</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{tiktokAccounts.map((a) => (
						<TableRow className="h-14" key={a.handle}>
							<TableCell className="ps-6">
								<div className="flex items-center gap-3">
									<Avatar className="size-8 rounded-md">
										<AvatarImage src={a.avatar} />
										<AvatarFallback>{a.handle.charAt(1)}</AvatarFallback>
									</Avatar>
									<div className="flex flex-col">
										<span className="font-medium">{a.handle}</span>
										<span className="text-muted-foreground text-xs">
											{a.niche}
										</span>
									</div>
								</div>
							</TableCell>
							<TableCell className="text-right tabular-nums">
								{formatCompactNumber(a.followers)}
							</TableCell>
							<TableCell className="text-right tabular-nums">
								{formatCompactNumber(a.views)}
							</TableCell>
							<TableCell className="text-right tabular-nums">
								{formatCompactNumber(a.likes)}
							</TableCell>
							<TableCell className="text-right tabular-nums">{a.posts}</TableCell>
							<TableCell className="text-right tabular-nums">
								{a.engagement.toFixed(1)}%
							</TableCell>
							<TableCell className="pe-6 text-right">
								<Delta className="justify-end" value={a.delta}>
									<DeltaIcon variant="arrow" />
									<DeltaValue />
								</Delta>
							</TableCell>
						</TableRow>
					))}
				</TableBody>
			</Table>
		</DashboardCard>
	);
}
