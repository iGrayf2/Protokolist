from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from .segments import TranscriptSegment

DEFAULT_DICTIONARY_PATH = Path("config") / "dictionary.json"


def load_dictionary(path: str | Path = DEFAULT_DICTIONARY_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        return {"phrase_replacements": {}, "preferred_terms": []}
    return json.loads(path.read_text(encoding="utf-8"))


def cleanup_text(text: str, dictionary: dict | None = None) -> str:
    dictionary = dictionary or load_dictionary()
    cleaned = text.strip()
    replacements = dictionary.get("phrase_replacements", {})
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    cleaned = " ".join(cleaned.split())
    return cleaned


def cleanup_segments(segments: list[TranscriptSegment], dictionary: dict | None = None) -> list[TranscriptSegment]:
    dictionary = dictionary or load_dictionary()
    cleaned_segments: list[TranscriptSegment] = []
    for segment in segments:
        raw_text = segment.raw_text or segment.text
        cleaned_segments.append(
            replace(
                segment,
                raw_text=raw_text,
                text=cleanup_text(raw_text, dictionary),
            )
        )
    return cleaned_segments
