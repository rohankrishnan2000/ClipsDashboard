from __future__ import annotations

import json
from typing import Any

from openai import OpenAI


SYSTEM_PROMPT = """
You are an expert short-form video clipping assistant.

Find moments from livestream transcripts that would make strong raw clip candidates.
Prioritize conflict, humor, surprise, drama, strong opinions, useful context, and moments
with a clear setup and payoff. Avoid dead air, contextless fragments, and timestamps not
present in the transcript.

Return only valid JSON.
"""


def analyze_transcript(
    transcript: dict[str, Any],
    *,
    api_key: str,
    model: str,
    clip_count: int,
    chunk_seconds: int = 600,
) -> dict[str, Any]:
    client = OpenAI(api_key=api_key)
    segments = clean_segments(transcript)
    chunks = split_segments_by_time(segments, chunk_seconds)
    chunk_results = []

    for index, chunk in enumerate(chunks):
        chunk_text = segments_to_llm_text(chunk)
        chunk_results.append(_call_openai_for_clips(client, model, chunk_text, index))

    clips = merge_and_sort_clips(chunk_results)
    clips = dedupe_clips(clips)
    clips = clips[:clip_count]
    return {
        "model": model,
        "clip_count": clip_count,
        "total_candidates": sum(len(result.get("clips", [])) for result in chunk_results),
        "clips": clips,
    }


def clean_segments(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    cleaned = []
    for segment in transcript.get("segments", []):
        text = str(segment.get("text") or "").strip()
        start = segment.get("start")
        end = segment.get("end")
        if start is None or end is None or not text:
            continue
        cleaned.append({"start": float(start), "end": float(end), "text": text})
    return cleaned


def split_segments_by_time(segments: list[dict[str, Any]], chunk_seconds: int) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_start: float | None = None
    for segment in segments:
        if current_start is None:
            current_start = segment["start"]
        if segment["start"] - current_start >= chunk_seconds and current:
            chunks.append(current)
            current = []
            current_start = segment["start"]
        current.append(segment)
    if current:
        chunks.append(current)
    return chunks


def segments_to_llm_text(segments: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"[{format_time(seg['start'])}-{format_time(seg['end'])} | "
        f"{seg['start']:.2f}-{seg['end']:.2f}] {seg['text']}"
        for seg in segments
    )


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _call_openai_for_clips(client: OpenAI, model: str, chunk_text: str, chunk_index: int) -> dict[str, Any]:
    user_prompt = f"""
Analyze this transcript chunk and find the best clip-worthy moments.

Return JSON in this exact shape:
{{
  "chunk_index": {chunk_index},
  "clips": [
    {{
      "start_time": 123.45,
      "end_time": 175.20,
      "start_label": "02:03",
      "end_label": "02:55",
      "title": "Short catchy title",
      "hook": "The opening line or idea that makes people keep watching",
      "reason": "Why this would make a good short-form clip",
      "score": 8,
      "clip_type": "funny | drama | reaction | story | opinion | roast | informational | other"
    }}
  ]
}}

Rules:
- Return 3-8 clips max for this chunk.
- Each clip should usually be 15-90 seconds.
- Prefer fewer strong clips over many weak clips.
- start_time and end_time must be numbers in seconds.
- Use transcript timestamps only.
- Do not return clips with score below 6 unless there are no good clips.

Transcript chunk:
{chunk_text}
"""
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "clip_results",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "chunk_index": {"type": "integer"},
                        "clips": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "start_time": {"type": "number"},
                                    "end_time": {"type": "number"},
                                    "start_label": {"type": "string"},
                                    "end_label": {"type": "string"},
                                    "title": {"type": "string"},
                                    "hook": {"type": "string"},
                                    "reason": {"type": "string"},
                                    "score": {"type": "number"},
                                    "clip_type": {"type": "string"},
                                },
                                "required": [
                                    "start_time",
                                    "end_time",
                                    "start_label",
                                    "end_label",
                                    "title",
                                    "hook",
                                    "reason",
                                    "score",
                                    "clip_type",
                                ],
                            },
                        },
                    },
                    "required": ["chunk_index", "clips"],
                },
            }
        },
    )
    return json.loads(response.output_text)


def merge_and_sort_clips(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clips: list[dict[str, Any]] = []
    for result in results:
        clips.extend(result.get("clips", []))
    return sorted(clips, key=lambda clip: clip.get("score", 0), reverse=True)


def dedupe_clips(clips: list[dict[str, Any]], overlap_seconds: float = 8.0) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    for clip in clips:
        start = float(clip.get("start_time") or 0)
        end = float(clip.get("end_time") or 0)
        if end <= start:
            continue
        duplicate = any(
            abs(start - float(existing.get("start_time") or 0)) < overlap_seconds
            or ranges_overlap(start, end, float(existing.get("start_time") or 0), float(existing.get("end_time") or 0))
            for existing in deduped
        )
        if not duplicate:
            deduped.append(clip)
    return deduped


def ranges_overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)
