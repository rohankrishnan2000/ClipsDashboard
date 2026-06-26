"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetFooter,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import {
	getConfig,
	publishToTikTok,
	type AppConfig,
} from "@/lib/api";
import { AlertCircleIcon, SendIcon, UploadIcon } from "lucide-react";

type PublishTarget = {
	jobId: string;
	filename: string;
	title: string;
};

type PublishMode = "draft" | "direct";

export function PublishSheet({
	target,
	trigger,
}: {
	target: PublishTarget;
	trigger: React.ReactNode;
}) {
	const [open, setOpen] = useState(false);
	const [config, setConfig] = useState<AppConfig | null>(null);
	const [mode, setMode] = useState<PublishMode>("draft");
	const [caption, setCaption] = useState(target.title);
	const [accessToken, setAccessToken] = useState("");
	const [privacy, setPrivacy] = useState<
		"PUBLIC_TO_EVERYONE" | "SELF_ONLY" | "FOLLOWER_OF_CREATOR" | "MUTUAL_FOLLOW_FRIENDS"
	>("SELF_ONLY");
	const [submitting, setSubmitting] = useState(false);

	useEffect(() => {
		if (!open || config) {
			return;
		}
		getConfig()
			.then(setConfig)
			.catch(() => setConfig(null));
	}, [open, config]);

	async function submit() {
		if (!accessToken.trim()) {
			toast.error("Paste a TikTok access token to publish.");
			return;
		}
		setSubmitting(true);
		try {
			const res = await publishToTikTok({
				job_id: target.jobId,
				filename: target.filename,
				access_token: accessToken.trim(),
				caption,
				mode,
				privacy_level: privacy,
			});
			toast.success(
				mode === "draft"
					? "Sent to your TikTok drafts/inbox"
					: "Direct post started",
				{ description: `publish_id ${res.publish_id.slice(0, 12)}…` }
			);
			setOpen(false);
		} catch (err) {
			toast.error("Publish failed", {
				description: err instanceof Error ? err.message : "Unknown error.",
			});
		} finally {
			setSubmitting(false);
		}
	}

	const tiktokReady = config?.tiktok_configured ?? false;

	return (
		<Sheet onOpenChange={setOpen} open={open}>
			<SheetTrigger asChild>{trigger}</SheetTrigger>
			<SheetContent className="flex w-full flex-col gap-0 sm:max-w-md">
				<SheetHeader>
					<SheetTitle>Publish to TikTok</SheetTitle>
					<SheetDescription className="truncate">{target.title}</SheetDescription>
				</SheetHeader>

				<div className="flex flex-1 flex-col gap-5 overflow-y-auto px-4 py-2">
					{config && !tiktokReady && (
						<Alert variant="destructive">
							<AlertCircleIcon />
							<AlertTitle>TikTok not connected yet</AlertTitle>
							<AlertDescription>
								Add your TikTok app credentials (TIKTOK_CLIENT_KEY /
								TIKTOK_CLIENT_SECRET) on the backend and run the OAuth flow.
								See SETUP_TODO.md. You can still fill this out to test once
								connected.
							</AlertDescription>
						</Alert>
					)}

					<div className="flex flex-col gap-2">
						<span className="font-medium text-sm">Destination</span>
						<div className="grid grid-cols-2 gap-2">
							<Button
								onClick={() => setMode("draft")}
								type="button"
								variant={mode === "draft" ? "default" : "outline"}
							>
								<UploadIcon data-icon="inline-start" />
								Drafts / inbox
							</Button>
							<Button
								onClick={() => setMode("direct")}
								type="button"
								variant={mode === "direct" ? "default" : "outline"}
							>
								<SendIcon data-icon="inline-start" />
								Direct post
							</Button>
						</div>
						<p className="text-muted-foreground text-xs">
							{mode === "draft"
								? "Uploads to the creator's TikTok inbox to finish in-app (video.upload scope)."
								: "Publishes immediately with the privacy level below (video.publish scope)."}
						</p>
					</div>

					<div className="flex flex-col gap-2">
						<span className="font-medium text-sm">Caption</span>
						<Textarea
							onChange={(e) => setCaption(e.target.value)}
							placeholder="Write a caption…"
							rows={3}
							value={caption}
						/>
					</div>

					{mode === "direct" && (
						<div className="flex flex-col gap-2">
							<span className="font-medium text-sm">Privacy</span>
							<Select
								onValueChange={(v) => setPrivacy(v as typeof privacy)}
								value={privacy}
							>
								<SelectTrigger>
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="SELF_ONLY">Private (only me)</SelectItem>
									<SelectItem value="FOLLOWER_OF_CREATOR">Followers</SelectItem>
									<SelectItem value="MUTUAL_FOLLOW_FRIENDS">Friends</SelectItem>
									<SelectItem value="PUBLIC_TO_EVERYONE">Public</SelectItem>
								</SelectContent>
							</Select>
						</div>
					)}

					<div className="flex flex-col gap-2">
						<span className="font-medium text-sm">Access token</span>
						<Input
							onChange={(e) => setAccessToken(e.target.value)}
							placeholder="TikTok user access token"
							type="password"
							value={accessToken}
						/>
						<p className="text-muted-foreground text-xs">
							Temporary: paste a per-account token from the OAuth flow. Token
							storage per account is groundwork to be wired up (see
							SETUP_TODO.md).
						</p>
					</div>
				</div>

				<SheetFooter>
					<Button disabled={submitting} onClick={submit}>
						{submitting ? (
							<>
								<Spinner data-icon="inline-start" />
								Publishing…
							</>
						) : mode === "draft" ? (
							"Send to drafts"
						) : (
							"Publish now"
						)}
					</Button>
				</SheetFooter>
			</SheetContent>
		</Sheet>
	);
}
