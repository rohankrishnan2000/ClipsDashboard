from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio_chunks(
    video_path: Path,
    audio_dir: Path,
    segment_seconds: int = 600,
) -> list[Path]:
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = audio_dir / "chunk_%03d.mp3"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        "-f",
        "segment",
        "-segment_time",
        str(segment_seconds),
        str(output_pattern),
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace")[-1200:])

    chunks = sorted(audio_dir.glob("chunk_*.mp3"))
    if not chunks:
        raise FileNotFoundError("No audio chunks were created")
    return chunks
