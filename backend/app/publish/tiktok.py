"""TikTok Content Posting API groundwork.

This wraps TikTok's Content Posting API so a finished clip can be sent
either as a **direct post** (published immediately) or uploaded to the
creator's **drafts/inbox** for them to finish in the TikTok app.

NONE of this works until you, the user, do the following (see TODO.md):
  1. Create a TikTok app at https://developers.tiktok.com/
  2. Enable the "Content Posting API" product and request the
     `video.publish` (direct post) and/or `video.upload` (drafts) scopes.
  3. Put TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / TIKTOK_REDIRECT_URI in
     your .env, and run the OAuth flow to obtain a per-account access token.

Tokens are NOT persisted here yet — `access_token` is passed in by the
caller. Wire up token storage per TikTok account when you connect things.

Reference: https://developers.tiktok.com/doc/content-posting-api-get-started
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlencode

import requests

from ..settings import Settings

OPEN_API = "https://open.tiktokapis.com"
AUTH_BASE = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = f"{OPEN_API}/v2/oauth/token/"

PrivacyLevel = Literal[
    "PUBLIC_TO_EVERYONE",
    "MUTUAL_FOLLOW_FRIENDS",
    "FOLLOWER_OF_CREATOR",
    "SELF_ONLY",
]


class TikTokNotConfigured(RuntimeError):
    pass


class TikTokError(RuntimeError):
    pass


@dataclass
class TikTokPublishResult:
    publish_id: str
    status: str
    mode: str  # "direct" | "draft"


class TikTokClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.tiktok_configured:
            raise TikTokNotConfigured(
                "TikTok is not configured. Set TIKTOK_CLIENT_KEY and "
                "TIKTOK_CLIENT_SECRET in your .env (see TODO.md)."
            )
        self.settings = settings

    # ── OAuth ────────────────────────────────────────────────────────
    def authorize_url(self, state: str) -> str:
        """URL to send a creator to so they can grant posting access."""
        params = {
            "client_key": self.settings.tiktok_client_key,
            "scope": self.settings.tiktok_scopes,
            "response_type": "code",
            "redirect_uri": self.settings.tiktok_redirect_uri,
            "state": state,
        }
        return f"{AUTH_BASE}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange the OAuth `code` for an access/refresh token bundle.

        TODO(user): persist the returned tokens per TikTok account so
        publishing can look them up later.
        """
        resp = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": self.settings.tiktok_client_key,
                "client_secret": self.settings.tiktok_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.settings.tiktok_redirect_uri,
            },
            timeout=30,
        )
        return self._json(resp)

    def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        resp = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": self.settings.tiktok_client_key,
                "client_secret": self.settings.tiktok_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=30,
        )
        return self._json(resp)

    # ── Creator info (required before direct post) ───────────────────
    def creator_info(self, access_token: str) -> dict[str, Any]:
        """Query the creator's allowed privacy levels, posting limits, etc.

        TikTok requires calling this before a direct post so the UI can
        show the correct privacy options.
        """
        resp = requests.post(
            f"{OPEN_API}/v2/post/publish/creator_info/query/",
            headers=self._auth_headers(access_token),
            timeout=30,
        )
        return self._json(resp).get("data", {})

    # ── Publishing ───────────────────────────────────────────────────
    def post_from_url(
        self,
        access_token: str,
        *,
        video_url: str,
        caption: str = "",
        privacy_level: PrivacyLevel = "SELF_ONLY",
        mode: Literal["direct", "draft"] = "draft",
        disable_comment: bool = False,
        disable_duet: bool = False,
        disable_stitch: bool = False,
    ) -> TikTokPublishResult:
        """Publish a clip that is already hosted at a public URL.

        `mode="draft"` uploads to the creator's TikTok inbox (uses the
        `video.upload` scope); `mode="direct"` publishes immediately (uses
        the `video.publish` scope and requires `privacy_level`).

        The video URL's domain must be verified in your TikTok app's
        "URL prefix" settings for PULL_FROM_URL to be accepted.
        """
        source_info = {"source": "PULL_FROM_URL", "video_url": video_url}

        if mode == "draft":
            endpoint = f"{OPEN_API}/v2/post/publish/inbox/video/init/"
            payload: dict[str, Any] = {"source_info": source_info}
        else:
            endpoint = f"{OPEN_API}/v2/post/publish/video/init/"
            payload = {
                "post_info": {
                    "title": caption,
                    "privacy_level": privacy_level,
                    "disable_comment": disable_comment,
                    "disable_duet": disable_duet,
                    "disable_stitch": disable_stitch,
                },
                "source_info": source_info,
            }

        resp = requests.post(
            endpoint,
            headers=self._auth_headers(access_token),
            json=payload,
            timeout=60,
        )
        data = self._json(resp).get("data", {})
        publish_id = data.get("publish_id", "")
        if not publish_id:
            raise TikTokError(f"TikTok did not return a publish_id: {data}")
        return TikTokPublishResult(publish_id=publish_id, status="PROCESSING", mode=mode)

    def publish_status(self, access_token: str, publish_id: str) -> dict[str, Any]:
        """Poll the status of an in-flight publish."""
        resp = requests.post(
            f"{OPEN_API}/v2/post/publish/status/fetch/",
            headers=self._auth_headers(access_token),
            json={"publish_id": publish_id},
            timeout=30,
        )
        return self._json(resp).get("data", {})

    # ── helpers ──────────────────────────────────────────────────────
    def _auth_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    @staticmethod
    def _json(resp: requests.Response) -> dict[str, Any]:
        try:
            body = resp.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise TikTokError(f"Non-JSON response from TikTok ({resp.status_code})") from exc
        error = body.get("error")
        if error and error.get("code") not in (None, "ok"):
            raise TikTokError(error.get("message") or str(error))
        return body
