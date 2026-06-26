import { PageHeading } from "@/components/page-heading";
import { StudioIntegrations } from "@/components/studio/integrations";

export default function StudioPage() {
	return (
		<div className="flex flex-col">
			<PageHeading
				title="Studio"
				description="Publishing destinations and processing infrastructure for your clips."
			/>
			<StudioIntegrations />
		</div>
	);
}
