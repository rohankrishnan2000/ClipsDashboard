import { notFound } from "next/navigation";
import { PageHeading } from "@/components/page-heading";
import { StreamerDetail } from "@/components/clips/streamer-detail";
import { getStreamer, streamers } from "@/lib/data";

export function generateStaticParams() {
	return streamers.map((s) => ({ streamer: s.slug }));
}

export default async function StreamerPage({
	params,
	searchParams,
}: {
	params: Promise<{ streamer: string }>;
	searchParams: Promise<{ tab?: string }>;
}) {
	const { streamer: slug } = await params;
	const { tab } = await searchParams;
	const streamer = getStreamer(slug);

	if (!streamer) {
		notFound();
	}

	const initialTab = tab === "clips" ? "clips" : "videos";

	return (
		<div className="flex flex-col">
			<PageHeading
				title={streamer.name}
				description="Review footage, send videos for processing, and manage generated clips."
			/>
			<StreamerDetail initialTab={initialTab} streamer={streamer} />
		</div>
	);
}
