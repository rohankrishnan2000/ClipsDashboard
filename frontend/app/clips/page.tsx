import { PageHeading } from "@/components/page-heading";
import { ClipsTabs } from "@/components/clips/clips-tabs";

export default function ClipsPage() {
	return (
		<div className="flex flex-col">
			<PageHeading
				title="Clips"
				description="Manage footage per streamer. Open a streamer to send videos for processing."
			/>
			<ClipsTabs />
		</div>
	);
}
