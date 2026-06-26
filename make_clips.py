#!/usr/bin/env python3
"""
Cut video clips from a source file based on timestamps in a clips JSON.

Usage:
    python make_clips.py --video "/path/to/source.mp4" --clips clips.json
    python make_clips.py --video source.mp4 --clips clips.json --outdir clips_out
    python make_clips.py --video source.mp4 --clips clips.json --copy   # fast, keyframe-aligned
    python make_clips.py --video source.mp4 --clips clips.json --min-score 7

The clips JSON is expected to look like the output of eval_clip_script.py:
    { "clips": [ {"start_time": 88.78, "end_time": 114.06, "title": "...", "score": 8}, ... ] }
"""

import argparse
import json
import os
import re
import subprocess
import sys


def slugify(text: str, max_len: int = 60) -> str:
    """Turn a clip title into a safe filename fragment."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)      # drop punctuation
    text = re.sub(r"[\s_-]+", "_", text)      # collapse whitespace to _
    text = text.strip("_")
    return text[:max_len] or "clip"


def load_clips(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Accept either {"clips": [...]} or a bare list
    clips = data.get("clips", data) if isinstance(data, dict) else data
    if not isinstance(clips, list):
        sys.exit(f"Could not find a clips array in {path}")
    return clips


def build_ffmpeg_cmd(video, start, duration, out_path, copy):
    if copy:
        # Stream copy: very fast, but cuts snap to the nearest keyframe (less precise).
        # -ss before -i for fast seek.
        return [
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}",
            "-i", video,
            "-t", f"{duration:.3f}",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            out_path,
        ]
    # Re-encode: frame-accurate cuts (better for short-form). -ss after -i.
    return [
        "ffmpeg", "-y",
        "-i", video,
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        out_path,
    ]


def main():
    ap = argparse.ArgumentParser(description="Cut clips from a video using a clips JSON.")
    ap.add_argument("--video", required=True, help="Path to the source video file.")
    ap.add_argument("--clips", default="clips.json", help="Path to the clips JSON.")
    ap.add_argument("--outdir", default="clips_out", help="Directory to write clips into.")
    ap.add_argument("--copy", action="store_true",
                    help="Stream-copy instead of re-encoding (fast, keyframe-aligned).")
    ap.add_argument("--min-score", type=float, default=None,
                    help="Only cut clips with score >= this value.")
    ap.add_argument("--pad", type=float, default=0.0,
                    help="Seconds of padding to add before start and after end.")
    args = ap.parse_args()

    if not os.path.isfile(args.video):
        sys.exit(f"Source video not found: {args.video}")

    clips = load_clips(args.clips)
    os.makedirs(args.outdir, exist_ok=True)

    ext = ".mp4"
    made, skipped = 0, 0

    for i, clip in enumerate(clips, start=1):
        try:
            start = float(clip["start_time"])
            end = float(clip["end_time"])
        except (KeyError, TypeError, ValueError):
            print(f"[{i}] skipping: missing/invalid start_time or end_time")
            skipped += 1
            continue

        score = clip.get("score")
        if args.min_score is not None and score is not None and score < args.min_score:
            print(f"[{i}] skipping: score {score} < min-score {args.min_score}")
            skipped += 1
            continue

        start = max(0.0, start - args.pad)
        end = end + args.pad
        duration = end - start
        if duration <= 0:
            print(f"[{i}] skipping: non-positive duration ({duration:.2f}s)")
            skipped += 1
            continue

        title = clip.get("title", f"clip_{i}")
        out_name = f"{i:02d}_{slugify(title)}{ext}"
        out_path = os.path.join(args.outdir, out_name)

        print(f"[{i}] {start:.2f}->{end:.2f} ({duration:.2f}s) score={score}  -> {out_name}")

        cmd = build_ffmpeg_cmd(args.video, start, duration, out_path, args.copy)
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"[{i}] ffmpeg failed:\n{result.stderr.decode(errors='replace')[-800:]}")
            skipped += 1
            continue
        made += 1

    print(f"\nDone. {made} clip(s) written to {args.outdir}/  ({skipped} skipped)")


if __name__ == "__main__":
    main()
