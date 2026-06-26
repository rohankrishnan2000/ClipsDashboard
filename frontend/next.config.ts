import type { NextConfig } from "next";

// Proxy /api/* to the FastAPI backend so the frontend can call it same-origin
// (no CORS). Override the target with BACKEND_URL when needed.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
	async rewrites() {
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
