from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


def cut_raw_clips(video_path: Path, clips: list[dict[str, Any]], output_dir: Path) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    enriched: list[dict[str, Any]] = []
    for index, clip in enumerate(clips, start=1):
        start = float(clip["start_time"])
        end = float(clip["end_time"])
        duration = max(0.0, end - start)
        if duration <= 0:
            continue

        filename = f"{index:02d}_{slugify(str(clip.get('title') or f'clip_{index}'))}.mp4"
        output_path = output_dir / filename
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        updated = dict(clip)
        if result.returncode == 0:
            updated["filename"] = filename
        else:
            updated["cut_error"] = result.stderr.decode(errors="replace")[-800:]
        enriched.append(updated)
    return enriched


def slugify(text: str, max_len: int = 60) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    text = text.strip("_")
    return text[:max_len] or "clip"
