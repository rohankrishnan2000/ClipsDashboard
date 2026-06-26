import { Button } from "@/components/ui/button";
import { PageHeading } from "@/components/page-heading";
import { TikTokStats } from "@/components/dashboard/tiktok-stats";
import { ViewsChart } from "@/components/dashboard/views-chart";
import { AccountsTable } from "@/components/dashboard/accounts-table";
import { TopClips } from "@/components/dashboard/top-clips";
import { DownloadIcon } from "lucide-react";

export default function DashboardPage() {
	return (
		<div className="flex flex-col">
			<PageHeading
				title="Dashboard"
				description="TikTok performance across every account you publish to."
				actions={
					<Button variant="outline">
						<DownloadIcon data-icon="inline-start" />
						Export report
					</Button>
				}
			/>
			<div className="grid grid-cols-1 gap-px bg-border p-px md:grid-cols-2 lg:grid-cols-4">
				<TikTokStats />
				<ViewsChart />
				<TopClips />
				<AccountsTable />
			</div>
		</div>
	);
}
