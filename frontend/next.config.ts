import type { NextConfig } from "next";

// The frontend talks to the FastAPI backend over /api/*. In local dev we
// proxy those requests to the backend so everything is same-origin (no CORS).
//
// On Vercel the backend is NOT on the same host, so set BACKEND_URL in the
// Vercel project env vars to your deployed backend (e.g. the Vultr VPS:
// https://api.yourdomain.com). When BACKEND_URL is unset in production we
// skip the rewrite instead of proxying to localhost (which would 502).
const BACKEND_URL =
	process.env.BACKEND_URL ??
	(process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

const nextConfig: NextConfig = {
	async rewrites() {
		if (!BACKEND_URL) {
			return [];
		}
		return [
			{
				source: "/api/:path*",
				destination: `${BACKEND_URL}/api/:path*`,
			},
		];
	},
	images: {
		remotePatterns: [{ protocol: "https", hostname: "images.kick.com" }],
	},
};

export default nextConfig;
