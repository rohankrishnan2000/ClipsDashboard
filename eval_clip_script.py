from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from typing import List, Dict, Any

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INPUT_PATH = "/Users/rohankrishnan/Coding/clipping_bot/transcript.json"
OUTPUT_PATH = "/Users/rohankrishnan/Coding/clipping_bot/clips.json"

# Cheap/good first choice. You can switch to a stronger model later.
MODEL = "gpt-4.1-mini"

# For a first version, 8-12 minutes per LLM chunk is fine if transcript is not insane.
# Since your current transcript chunk is ~10 minutes, this fits perfectly.
CHUNK_SECONDS = 600


SYSTEM_PROMPT = """
You are an expert short-form video clipping assistant.

Your job is to analyze livestream/podcast transcript segments and find moments that would make good clips for TikTok, YouTube Shorts, Instagram Reels, or Twitter/X.

Prioritize moments that have:
- curse words, slurs, or edgy content (these often perform well in short-form)
- anything to do with picking up women, dating, or relationships
- conflict, drama, surprise, humor, embarrassment, debate, or a strong opinion
- anything related to plastic surgeries, looksmaxing, or doing things to look better. pay attention for the word mog
- enough context to make sense as a standalone clip
- a clear beginning and ending
- spoken content that could reasonably become a 15-90 second clip

Avoid:
- dead air
- repeated filler
- moments that are only "yeah", "oh", laughter, or silence
- clips that require too much outside context
- extremely short moments unless they are very funny or shocking
- making up timestamps not present in the transcript

Rules:
- Use the timestamps provided.
- You may slightly expand start/end times to capture context.
- Return only valid JSON.
- Do not include markdown.
- Do not include commentary outside the JSON.

Scoring:
10 = extremely viral / obvious clip
7-9 = strong clip
4-6 = usable but not amazing
1-3 = weak, probably skip
"""


def load_transcript(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_time(seconds: float) -> str:
    """
    Converts seconds into MM:SS format.
    Example: 95.4 -> 01:35
    """
    seconds = int(seconds)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def clean_segments(transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Keeps only the fields the LLM needs.
    Removes Whisper debugging fields like tokens, avg_logprob, temperature, etc.
    """
    cleaned = []

    for seg in transcript.get("segments", []):
        text = seg.get("text", "").strip()
        start = seg.get("start")
        end = seg.get("end")

        if start is None or end is None:
            continue

        # Skip totally empty text
        if not text:
            continue

        cleaned.append({
            "start": float(start),
            "end": float(end),
            "text": text
        })

    return cleaned


def split_segments_by_time(
    segments: List[Dict[str, Any]],
    chunk_seconds: int = CHUNK_SECONDS
) -> List[List[Dict[str, Any]]]:
    """
    Splits transcript into time windows, like 0-600 sec, 600-1200 sec, etc.
    """
    chunks = []
    current_chunk = []
    current_chunk_start = None

    for seg in segments:
        if current_chunk_start is None:
            current_chunk_start = seg["start"]

        if seg["start"] - current_chunk_start >= chunk_seconds and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_chunk_start = seg["start"]

        current_chunk.append(seg)

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def segments_to_llm_text(segments: List[Dict[str, Any]]) -> str:
    """
    Converts JSON segments into a simple readable transcript format.
    This is better for LLMs than raw Whisper JSON.
    """
    lines = []

    for seg in segments:
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]

        lines.append(
            f"[{format_time(start)}-{format_time(end)} | {start:.2f}-{end:.2f}] {text}"
        )

    return "\n".join(lines)


def build_user_prompt(chunk_text: str, chunk_index: int) -> str:
    return f"""
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

Important:
- Return 3-8 clips max.
- Each clip should usually be 15-90 seconds.
- Prefer fewer strong clips over many weak clips.
- start_time and end_time must be numbers in seconds.
- Use the transcript timestamps.
- Do not return clips with score below 6 unless there are no good clips.

Transcript chunk:

{chunk_text}
"""


def call_openai_for_clips(chunk_text: str, chunk_index: int) -> Dict[str, Any]:
    """
    Calls OpenAI and asks for structured JSON.
    The Responses API is OpenAI's current text-generation API, and it supports
    structured outputs / JSON schema style responses.
    """

    user_prompt = build_user_prompt(chunk_text, chunk_index)

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "clip_results",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "chunk_index": {
                            "type": "integer"
                        },
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
                                    "score": {"type": "integer"},
                                    "clip_type": {"type": "string"}
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
                                    "clip_type"
                                ]
                            }
                        }
                    },
                    "required": ["chunk_index", "clips"]
                }
            }
        }
    )

    return json.loads(response.output_text)


def merge_and_sort_clips(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_clips = []

    for result in results:
        for clip in result.get("clips", []):
            all_clips.append(clip)

    # Sort best clips first
    all_clips.sort(key=lambda c: c.get("score", 0), reverse=True)

    return all_clips


def main():
    transcript = load_transcript(INPUT_PATH)
    segments = clean_segments(transcript)

    print(f"Loaded {len(segments)} transcript segments.")

    chunks = split_segments_by_time(segments, CHUNK_SECONDS)
    print(f"Split into {len(chunks)} LLM chunk(s).")

    all_results = []

    for i, chunk_segments in enumerate(chunks):
        print(f"Analyzing chunk {i + 1}/{len(chunks)}...")

        chunk_text = segments_to_llm_text(chunk_segments)
        result = call_openai_for_clips(chunk_text, i)

        all_results.append(result)

    clips = merge_and_sort_clips(all_results)

    output = {
        "source_file": INPUT_PATH,
        "model": MODEL,
        "total_clips": len(clips),
        "clips": clips
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(clips)} clips to {OUTPUT_PATH}")

    print("\nTop clips:")
    for clip in clips[:5]:
        print(
            f"- {clip['start_label']} to {clip['end_label']} "
            f"score={clip['score']} title={clip['title']}"
        )


if __name__ == "__main__":
    main()