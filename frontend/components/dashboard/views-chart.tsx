"use client";

import type * as React from "react";
import { Bar, BarChart, XAxis } from "recharts";
import {
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import {
	type ChartConfig,
	ChartContainer,
	ChartTooltip,
	ChartTooltipContent,
} from "@/components/ui/chart";
import { Delta, DeltaIcon, DeltaValue } from "@/components/delta";
import { DashboardCard } from "@/components/dashboard-card";
import { formatDate } from "@/components/formater";
import { viewsTrend } from "@/lib/data";

const first = viewsTrend[0].views;
const last = viewsTrend.at(-1)?.views ?? first;
const growthPct = Number((((last - first) / first) * 100).toFixed(1));

const chartConfig = {
	views: {
		label: "Views",
		color: "var(--chart-2)",
	},
} satisfies ChartConfig;

function GradientBar(
	props: React.SVGProps<SVGRectElement> & { index?: number }
) {
	const { fill, x = 0, y = 0, width = 0, height = 0, index = 0 } = props;
	const gid = `views-bar-${index}`;
	return (
		<>
			<rect
				fill={`url(#${gid})`}
				height={height}
				stroke="none"
				width={width}
				x={x}
				y={y}
			/>
			<rect fill={fill} height={2} stroke="none" width={width} x={x} y={y} />
			<defs>
				<linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
					<stop offset="0%" stopColor={fill} stopOpacity={0.5} />
					<stop offset="100%" stopColor={fill} stopOpacity={0} />
				</linearGradient>
			</defs>
		</>
	);
}

export function ViewsChart() {
	return (
		<DashboardCard className="gap-0 md:col-span-2">
			<CardHeader className="gap-2">
				<div className="flex flex-wrap items-center gap-2">
					<CardTitle>TikTok views</CardTitle>
					<Delta value={growthPct} variant="badge">
						<DeltaIcon variant="trend" />
						<DeltaValue />
					</Delta>
				</div>
				<CardDescription>
					Daily views across all accounts, last 7 days.
				</CardDescription>
			</CardHeader>
			<CardContent>
				<ChartContainer
					className="aspect-auto h-60 w-full md:h-72"
					config={chartConfig}
				>
					<BarChart accessibilityLayer data={viewsTrend}>
						<XAxis
							axisLine={false}
							dataKey="date"
							interval={0}
							tickFormatter={(value) => formatDate(String(value), "day-month")}
							tickLine={false}
							tickMargin={10}
						/>
						<ChartTooltip
							content={<ChartTooltipContent hideLabel />}
							cursor={false}
						/>
						<Bar
							dataKey="views"
							fill="var(--color-views)"
							shape={<GradientBar />}
						/>
					</BarChart>
				</ChartContainer>
			</CardContent>
		</DashboardCard>
	);
}
