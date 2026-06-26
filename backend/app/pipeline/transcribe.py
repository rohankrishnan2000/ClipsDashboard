from __future__ import annotations

from pathlib import Path

from openai import OpenAI


def transcribe_audio_chunks(
    audio_chunks: list[Path],
    api_key: str,
    model: str,
    segment_seconds: int,
) -> dict:
    client = OpenAI(api_key=api_key)
    all_segments: list[dict] = []
    full_text: list[str] = []
    detected_language: str | None = None
    total_duration = 0.0

    for index, chunk_path in enumerate(audio_chunks):
        offset = index * segment_seconds
        with chunk_path.open("rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        data = transcript.model_dump()
        detected_language = detected_language or data.get("language")
        full_text.append(data.get("text", ""))
        total_duration = max(total_duration, offset + float(data.get("duration") or 0))

        for segment in data.get("segments", []):
            shifted = dict(segment)
            shifted["start"] = float(segment.get("start") or 0) + offset
            shifted["end"] = float(segment.get("end") or 0) + offset
            shifted["chunk_index"] = index
            all_segments.append(shifted)

    return {
        "duration": total_duration,
        "language": detected_language,
        "text": " ".join(text.strip() for text in full_text if text.strip()),
        "segments": all_segments,
    }
