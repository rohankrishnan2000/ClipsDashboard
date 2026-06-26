from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from curl_cffi import requests

from ..schemas import KickVideo


def fetch_recent_videos(username: str, months: int, limit: int = 10) -> list[KickVideo]:
    username = username.strip().lstrip("@")
    if not username:
        raise ValueError("Kick username is required")

    months = max(1, min(months, 36))
    cutoff = datetime.now(UTC) - timedelta(days=months * 31)
    url = f"https://kick.com/api/v2/channels/{username}/videos"
    referer = f"https://kick.com/{username}"

    headers = {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "referer": referer,
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "x-app-platform": "web",
    }

    session = requests.Session(impersonate="chrome124")
    session.get(referer, headers=headers, timeout=20)
    response = session.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    payload = response.json()
    raw_videos = _extract_video_list(payload)
    videos = [_normalize_video(item) for item in raw_videos]
    videos = [video for video in videos if video.url]
    filtered = [video for video in videos if _inside_window(video.created_at, cutoff)]
    return filtered[:limit]


def _extract_video_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "videos", "livestreams"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _normalize_video(item: dict[str, Any]) -> KickVideo:
    video_id = str(item.get("id") or item.get("video_id") or item.get("uuid") or item.get("slug") or "")
    title = item.get("session_title") or item.get("title") or "Untitled Kick VOD"
    url = item.get("url") or item.get("video_url") or item.get("source") or ""
    created_at = item.get("created_at") or item.get("start_time") or item.get("createdAt")
    duration = item.get("duration") or item.get("duration_sec") or item.get("duration_seconds")
    thumbnail = _thumbnail_url(
        item.get("thumbnail_url")
        or item.get("thumbnail")
        or item.get("thumbnail_src")
        or item.get("poster")
    )

    return KickVideo(
        id=video_id or url,
        title=str(title),
        url=str(url),
        created_at=str(created_at) if created_at else None,
        duration_sec=_duration_to_seconds(duration),
        thumbnail_url=thumbnail,
    )


def _duration_to_seconds(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = int(value)
        return seconds // 1000 if seconds > 86_400 else seconds
    text = str(value)
    if text.isdigit():
        return int(text)
    parts = text.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def _thumbnail_url(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        src = value.get("src") or value.get("url")
        return str(src) if src else None
    return str(value)


def _inside_window(created_at: str | None, cutoff: datetime) -> bool:
    if not created_at:
        return True
    parsed = _parse_datetime(created_at)
    if parsed is None:
        return True
    return parsed >= cutoff


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
