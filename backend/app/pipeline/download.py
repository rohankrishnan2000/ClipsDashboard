from __future__ import annotations

from pathlib import Path

from yt_dlp import YoutubeDL


def download_vod(vod_url: str, job_dir: Path) -> Path:
    output_template = str(job_dir / "source.%(ext)s")
    options = {
        "outtmpl": output_template,
        "format": "bv*+ba/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(vod_url, download=True)
        downloaded = Path(ydl.prepare_filename(info))

    mp4_path = job_dir / "source.mp4"
    if mp4_path.exists():
        return mp4_path
    if downloaded.exists():
        return downloaded

    matches = sorted(job_dir.glob("source.*"))
    if matches:
        return matches[0]
    raise FileNotFoundError("yt-dlp completed but no downloaded source file was found")
