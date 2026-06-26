"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { findActiveNavItem } from "@/components/app-shared";
import { getStreamer } from "@/lib/data";

export function AppBreadcrumbs() {
	const pathname = usePathname();
	const active = findActiveNavItem(pathname);

	if (!active) {
		return null;
	}

	// Deeper segment under /clips/[slug] → show the streamer name as a leaf.
	const streamerMatch = pathname.match(/^\/clips\/([^/]+)/);
	const streamer = streamerMatch ? getStreamer(streamerMatch[1]) : undefined;

	return (
		<Breadcrumb>
			<BreadcrumbList>
				<BreadcrumbItem>
					{streamer ? (
						<BreadcrumbLink asChild>
							<Link
								className="flex items-center gap-2 [&>svg]:size-3.5"
								href={active.path}
							>
								{active.icon}
								{active.title}
							</Link>
						</BreadcrumbLink>
					) : (
						<BreadcrumbPage className="flex items-center gap-2 [&>svg]:size-3.5">
							{active.icon}
							{active.title}
						</BreadcrumbPage>
					)}
				</BreadcrumbItem>
				{streamer && (
					<>
						<BreadcrumbSeparator />
						<BreadcrumbItem>
							<BreadcrumbPage>{streamer.name}</BreadcrumbPage>
						</BreadcrumbItem>
					</>
				)}
			</BreadcrumbList>
		</Breadcrumb>
	);
}
