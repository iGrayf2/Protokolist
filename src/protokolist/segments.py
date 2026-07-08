from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


def format_timestamp(seconds: float, always_hours: bool = True) -> str:
    seconds = max(0, float(seconds))
    millis = int(round((seconds - int(seconds)) * 1000))
    total_seconds = int(seconds)
    if millis == 1000:
        total_seconds += 1
        millis = 0

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if always_hours or hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_srt_timestamp(seconds: float) -> str:
    base = format_timestamp(seconds, always_hours=True)
    millis = int(round((max(0, float(seconds)) - int(max(0, float(seconds)))) * 1000))
    if millis == 1000:
        millis = 999
    return f"{base},{millis:03d}"
