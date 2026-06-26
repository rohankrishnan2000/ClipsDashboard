import { PageHeading } from "@/components/page-heading";
import { JobsView } from "@/components/jobs/jobs-view";

export default function JobsPage() {
	return (
		<div className="flex flex-col">
			<PageHeading
				title="Jobs"
				description="Track clipping jobs as they run and review, download, and publish the clips they produce."
			/>
			<JobsView />
		</div>
	);
}
