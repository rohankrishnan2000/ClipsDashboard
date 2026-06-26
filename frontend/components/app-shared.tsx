import type { ReactNode } from "react";
import {
	LayoutDashboardIcon,
	SearchIcon,
	ClapperboardIcon,
	WandSparklesIcon,
	ListVideoIcon,
	LifeBuoyIcon,
	BookOpenIcon,
} from "lucide-react";

export type SidebarNavItem = {
	title: string;
	path: string;
	icon?: ReactNode;
	subItems?: SidebarNavItem[];
};

export type SidebarNavGroup = {
	label?: string;
	items: SidebarNavItem[];
};

export const navGroups: SidebarNavGroup[] = [
	{
		label: "Overview",
		items: [
			{
				title: "Dashboard",
				path: "/",
				icon: <LayoutDashboardIcon />,
			},
			{
				title: "Search",
				path: "/search",
				icon: <SearchIcon />,
			},
		],
	},
	{
		label: "Production",
		items: [
			{
				title: "Jobs",
				path: "/jobs",
				icon: <ListVideoIcon />,
			},
			{
				title: "Clips",
				path: "/clips",
				icon: <ClapperboardIcon />,
			},
			{
				title: "Studio",
				path: "/studio",
				icon: <WandSparklesIcon />,
			},
		],
	},
];

export const footerNavLinks: SidebarNavItem[] = [
	{
		title: "Help Center",
		path: "/help",
		icon: <LifeBuoyIcon />,
	},
	{
		title: "Documentation",
		path: "/docs",
		icon: <BookOpenIcon />,
	},
];

export const navLinks: SidebarNavItem[] = [
	...navGroups.flatMap((group) =>
		group.items.flatMap((item) =>
			item.subItems?.length ? [item, ...item.subItems] : [item]
		)
	),
	...footerNavLinks,
];

/** Resolve the active nav item for a given pathname (most specific match wins). */
export function findActiveNavItem(pathname: string): SidebarNavItem | undefined {
	const matches = navLinks.filter(
		(item) =>
			item.path === pathname ||
			(item.path !== "/" && pathname.startsWith(item.path))
	);
	return matches.sort((a, b) => b.path.length - a.path.length)[0];
}
