"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { DashboardCard } from "@/components/dashboard-card";
import { getConfig, type AppConfig } from "@/lib/api";
import {
	AlertCircleIcon,
	CloudIcon,
	HardDriveIcon,
	ServerIcon,
	SparklesIcon,
} from "lucide-react";

type Integration = {
	key: keyof AppConfig | "openai";
	icon: ReactNode;
	title: string;
	connected: boolean;
	description: string;
	hint: string;
};

export function StudioIntegrations() {
	const [config, setConfig] = useState<AppConfig | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		getConfig()
			.then(setConfig)
			.catch((err) =>
				setError(err instanceof Error ? err.message : "Backend unreachable")
			);
	}, []);

	if (error) {
		return (
			<Alert variant="destructive">
				<AlertCircleIcon />
				<AlertTitle>Could not load integration status</AlertTitle>
				<AlertDescription>{error}</AlertDescription>
			</Alert>
		);
	}

	if (!config) {
		return (
			<div className="grid grid-cols-1 gap-px bg-border md:grid-cols-2">
				{Array.from({ length: 4 }).map((_, i) => (
					<DashboardCard className="gap-0" key={i}>
						<CardHeader className="gap-2">
							<Skeleton className="h-5 w-1/3" />
							<Skeleton className="h-4 w-2/3" />
						</CardHeader>
					</DashboardCard>
				))}
			</div>
		);
	}

	const integrations: Integration[] = [
		{
			key: "tiktok_configured",
			icon: <SparklesIcon className="size-5" />,
			title: "TikTok publishing",
			connected: config.tiktok_configured,
			description: "Post clips directly or push them to drafts/inbox.",
			hint: "Add TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET and run OAuth.",
		},
		{
			key: "vultr_configured",
			icon: <HardDriveIcon className="size-5" />,
			title: "Vultr object storage",
			connected: config.vultr_configured,
			description: "Store finished clips in S3-compatible cloud storage.",
			hint: "Set STORAGE_BACKEND=vultr and the VULTR_S3_* credentials.",
		},
		{
			key: "worker_configured",
			icon: <ServerIcon className="size-5" />,
			title: "Cloud processing worker",
			connected: config.worker_configured,
			description: "Offload download/transcribe/cut to a Vultr VPS.",
			hint: "Deploy the backend on a VPS and set WORKER_URL + token.",
		},
		{
			key: "openai",
			icon: <CloudIcon className="size-5" />,
			title: "OpenAI (transcribe + analyze)",
			connected: config.openai_configured,
			description: "Whisper transcription and LLM clip ranking.",
			hint: "Set OPENAI_API_KEY in the backend .env.",
		},
	];

	return (
		<div className="flex flex-col gap-6">
			<div className="grid grid-cols-1 gap-px bg-border md:grid-cols-2">
				{integrations.map((it) => (
					<DashboardCard className="gap-0" key={it.title}>
						<CardHeader className="gap-2">
							<div className="flex items-center gap-3">
								<span className="text-muted-foreground">{it.icon}</span>
								<CardTitle className="flex-1 text-base">{it.title}</CardTitle>
								<Badge variant={it.connected ? "default" : "outline"}>
									{it.connected ? "Connected" : "Not connected"}
								</Badge>
							</div>
							<CardDescription>{it.description}</CardDescription>
						</CardHeader>
						{!it.connected && (
							<CardContent className="text-muted-foreground text-xs">
								{it.hint} See <span className="font-medium">SETUP_TODO.md</span>.
							</CardContent>
						)}
					</DashboardCard>
				))}
			</div>

			<DashboardCard className="gap-0">
				<CardHeader>
					<CardTitle className="text-base">Publish your clips</CardTitle>
					<CardDescription>
						Clips are produced from the Jobs page. Open a finished job, preview a
						clip, and hit Publish to send it to TikTok.
					</CardDescription>
				</CardHeader>
				<CardContent>
					<Button asChild variant="outline">
						<a href="/jobs">Go to Jobs</a>
					</Button>
				</CardContent>
			</DashboardCard>
		</div>
	);
}
