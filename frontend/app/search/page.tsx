import { PageHeading } from "@/components/page-heading";
import { KickSearch } from "@/components/search/kick-search";

export default function SearchPage() {
	return (
		<div className="flex flex-col">
			<PageHeading
				title="Search"
				description="Find streams on Kick and pull them into your footage library."
			/>
			<KickSearch />
		</div>
	);
}
