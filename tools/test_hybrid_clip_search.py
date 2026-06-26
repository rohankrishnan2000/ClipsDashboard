from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-z0-9']+")

DEFAULT_QUERY = "clav sophie rain stream"

VIRALITY_TERMS = {
    "conflict": {
        "argue",
        "bitch",
        "drama",
        "fuck",
        "hate",
        "loser",
        "manipulate",
        "mean",
        "retard",
        "roast",
    },
    "dating": {"girl", "girls", "female", "love", "model", "sex", "woman", "women"},
    "looks": {"bb l", "bbl", "boobs", "jaw", "mog", "nose", "plastic", "surgery", "swelling"},
    "audience": {"chat", "comment", "donation", "tip", "tipped"},
    "reaction": {"look", "react", "really", "true", "what", "whoa", "yeah"},
}


@dataclass(frozen=True)
class Window:
    start: float
    end: float
    text: str
    tokens: list[str]


def load_segments(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        transcript = json.load(f)

    segments = []
    for segment in transcript.get("segments", []):
        text = str(segment.get("text") or "").strip()
        start = segment.get("start")
        end = segment.get("end")
        if text and start is not None and end is not None:
            segments.append({"start": float(start), "end": float(end), "text": text})
    return segments


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def make_windows(segments: list[dict[str, Any]], window_seconds: int, stride_seconds: int) -> list[Window]:
    if not segments:
        return []

    windows: list[Window] = []
    start = math.floor(segments[0]["start"] / stride_seconds) * stride_seconds
    final_end = segments[-1]["end"]

    while start < final_end:
        end = start + window_seconds
        included = [seg for seg in segments if seg["end"] > start and seg["start"] < end]
        text = " ".join(seg["text"] for seg in included).strip()
        if text:
            windows.append(Window(start=start, end=end, text=text, tokens=tokenize(text)))
        start += stride_seconds
    return windows


def idf_for_documents(documents: list[list[str]]) -> dict[str, float]:
    doc_count = len(documents)
    document_frequencies: Counter[str] = Counter()
    for doc in documents:
        document_frequencies.update(set(doc))
    return {
        term: math.log((doc_count - freq + 0.5) / (freq + 0.5) + 1.0)
        for term, freq in document_frequencies.items()
    }


def bm25_scores(query_tokens: list[str], documents: list[list[str]], *, k1: float = 1.5, b: float = 0.75) -> list[float]:
    if not documents:
        return []

    idf = idf_for_documents(documents)
    avg_len = sum(len(doc) for doc in documents) / len(documents)
    scores = []

    for doc in documents:
        frequencies = Counter(doc)
        doc_len = len(doc) or 1
        score = 0.0
        for term in query_tokens:
            tf = frequencies[term]
            if not tf:
                continue
            numerator = tf * (k1 + 1.0)
            denominator = tf + k1 * (1.0 - b + b * doc_len / avg_len)
            score += idf.get(term, 0.0) * numerator / denominator
        scores.append(score)
    return scores


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(tokens)
    length = len(tokens) or 1
    return {term: (count / length) * idf.get(term, 0.0) for term, count in counts.items()}


def cosine(a: dict[str, float] | list[float], b: dict[str, float] | list[float]) -> float:
    if isinstance(a, dict) and isinstance(b, dict):
        dot = sum(weight * b.get(term, 0.0) for term, weight in a.items())
        a_values = a.values()
        b_values = b.values()
    elif isinstance(a, list) and isinstance(b, list):
        dot = sum(a_value * b_value for a_value, b_value in zip(a, b, strict=False))
        a_values = a
        b_values = b
    else:
        raise TypeError("cosine inputs must both be sparse dicts or dense lists")
    a_norm = math.sqrt(sum(weight * weight for weight in a_values))
    b_norm = math.sqrt(sum(weight * weight for weight in b_values))
    if not a_norm or not b_norm:
        return 0.0
    return dot / (a_norm * b_norm)


def vector_scores(query_tokens: list[str], documents: list[list[str]]) -> list[float]:
    idf = idf_for_documents(documents + [query_tokens])
    query_vector = tfidf_vector(query_tokens, idf)
    return [cosine(query_vector, tfidf_vector(doc, idf)) for doc in documents]


def embedding_scores(
    query: str,
    windows: list[Window],
    *,
    model: str,
    cache_path: Path | None,
    batch_size: int = 96,
) -> list[float]:
    try:
        from dotenv import load_dotenv
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI embedding mode requires openai and python-dotenv packages.") from exc

    load_dotenv(dotenv_path=Path(".env"))
    cache_key = hashlib.sha256(
        json.dumps(
            {
                "model": model,
                "query": query,
                "windows": [{"start": window.start, "end": window.end, "text": window.text} for window in windows],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    if cache_path and cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("cache_key") == cache_key:
            return [cosine(cached["query_embedding"], embedding) for embedding in cached["window_embeddings"]]

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    inputs = [query] + [window.text for window in windows]
    embeddings = []
    for start in range(0, len(inputs), batch_size):
        response = client.embeddings.create(model=model, input=inputs[start : start + batch_size])
        embeddings.extend(item.embedding for item in response.data)

    query_embedding = embeddings[0]
    window_embeddings = embeddings[1:]

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "cache_key": cache_key,
                    "model": model,
                    "query_embedding": query_embedding,
                    "window_embeddings": window_embeddings,
                }
            ),
            encoding="utf-8",
        )

    return [cosine(query_embedding, embedding) for embedding in window_embeddings]


def virality_score(text: str, duration: float) -> float:
    lower = text.lower()
    tokens = tokenize(text)
    token_set = set(tokens)
    category_hits = 0
    term_hits = 0

    for terms in VIRALITY_TERMS.values():
        hits = 0
        for term in terms:
            if " " in term:
                hits += int(term in lower)
            else:
                hits += int(term in token_set)
        category_hits += int(hits > 0)
        term_hits += hits

    question_bonus = min(text.count("?"), 3) * 0.06
    exclamation_bonus = min(text.count("!"), 3) * 0.04
    duration_bonus = 0.16 if 20 <= duration <= 90 else 0.04
    density = min(term_hits / 12.0, 1.0)
    breadth = category_hits / len(VIRALITY_TERMS)
    return min((0.56 * density) + (0.28 * breadth) + duration_bonus + question_bonus + exclamation_bonus, 1.0)


def normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    max_score = max(scores)
    if max_score <= 0:
        return [0.0 for _ in scores]
    return [score / max_score for score in scores]


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def snippet(text: str, max_len: int = 260) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def main() -> None:
    parser = argparse.ArgumentParser(description="Test BM25 + vector + heuristic ranking on a transcript.")
    parser.add_argument("--transcript", default="transcript.json", help="Path to a transcript JSON file.")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Search query to rank transcript windows against.")
    parser.add_argument("--window-seconds", type=int, default=60, help="Candidate window size.")
    parser.add_argument("--stride-seconds", type=int, default=15, help="Step between candidate windows.")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results to print.")
    parser.add_argument("--output", help="Optional JSON path to save ranked results.")
    parser.add_argument("--bm25-weight", type=float, default=0.42)
    parser.add_argument("--vector-weight", type=float, default=0.28)
    parser.add_argument("--algorithm-weight", type=float, default=0.30)
    parser.add_argument("--vector-mode", choices=("tfidf", "openai"), default="tfidf")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--embedding-cache", help="Optional JSON cache path for OpenAI embeddings.")
    args = parser.parse_args()

    segments = load_segments(Path(args.transcript))
    windows = make_windows(segments, args.window_seconds, args.stride_seconds)
    documents = [window.tokens for window in windows]
    query_tokens = tokenize(args.query)

    bm25 = normalize(bm25_scores(query_tokens, documents))
    if args.vector_mode == "openai":
        vector = normalize(
            embedding_scores(
                args.query,
                windows,
                model=args.embedding_model,
                cache_path=Path(args.embedding_cache) if args.embedding_cache else None,
            )
        )
    else:
        vector = normalize(vector_scores(query_tokens, documents))
    algorithm = [virality_score(window.text, window.end - window.start) for window in windows]

    ranked = []
    for index, window in enumerate(windows):
        blended = (
            args.bm25_weight * bm25[index]
            + args.vector_weight * vector[index]
            + args.algorithm_weight * algorithm[index]
        )
        ranked.append(
            {
                "window": window,
                "score": blended,
                "bm25": bm25[index],
                "vector": vector[index],
                "algorithm": algorithm[index],
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)

    print(f'Query: "{args.query}"')
    print(f"Transcript: {args.transcript}")
    print(f"Segments: {len(segments)}")
    print(f"Candidate windows: {len(windows)} ({args.window_seconds}s window, {args.stride_seconds}s stride)")
    print(
        "Weights: "
        f"bm25={args.bm25_weight:.2f}, vector={args.vector_weight:.2f}, algorithm={args.algorithm_weight:.2f}"
    )
    print(f"Vector mode: {args.vector_mode}")
    if bm25 and max(bm25) == 0 and max(vector) == 0:
        print("Note: no exact query-token matches were found, so ranking is being driven by the algorithm score.")
    print()

    top_results = ranked[: args.top_k]

    if args.output:
        output = {
            "query": args.query,
            "transcript": args.transcript,
            "segments": len(segments),
            "candidate_windows": len(windows),
            "window_seconds": args.window_seconds,
            "stride_seconds": args.stride_seconds,
            "weights": {
                "bm25": args.bm25_weight,
                "vector": args.vector_weight,
                "algorithm": args.algorithm_weight,
            },
            "results": [
                {
                    "rank": rank,
                    "start": item["window"].start,
                    "end": item["window"].end,
                    "start_label": format_time(item["window"].start),
                    "end_label": format_time(item["window"].end),
                    "score": item["score"],
                    "bm25": item["bm25"],
                    "vector": item["vector"],
                    "algorithm": item["algorithm"],
                    "text": item["window"].text,
                }
                for rank, item in enumerate(top_results, start=1)
            ],
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved ranking JSON: {args.output}")
        print()

    for rank, item in enumerate(top_results, start=1):
        window = item["window"]
        print(
            f"{rank:>2}. {format_time(window.start)}-{format_time(window.end)} "
            f"score={item['score']:.3f} "
            f"bm25={item['bm25']:.3f} vector={item['vector']:.3f} algorithm={item['algorithm']:.3f}"
        )
        print(f"    {snippet(window.text)}")


if __name__ == "__main__":
    main()
