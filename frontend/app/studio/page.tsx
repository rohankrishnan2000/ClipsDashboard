import { PageHeading } from "@/components/page-heading";
import { Button } from "@/components/ui/button";
import {
	Empty,
	EmptyContent,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from "@/components/ui/empty";
import { WandSparklesIcon } from "lucide-react";

export default function StudioPage() {
	return (
		<div className="flex flex-col">
			<PageHeading
				title="Studio"
				description="Edit, caption, and publish your clips. Coming soon."
			/>
			<Empty className="border bg-background py-20">
				<EmptyHeader>
					<EmptyMedia variant="icon">
						<WandSparklesIcon />
					</EmptyMedia>
					<EmptyTitle>Studio is on the way</EmptyTitle>
					<EmptyDescription>
						A full editing suite for trimming, captioning, and scheduling clips
						straight to your TikTok accounts.
					</EmptyDescription>
				</EmptyHeader>
				<EmptyContent>
					<Button disabled variant="outline">
						Notify me when it&apos;s ready
					</Button>
				</EmptyContent>
			</Empty>
		</div>
	);
}
