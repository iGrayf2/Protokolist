from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TranscriptWord:
    start: float | None
    end: float | None
    word: str
    probability: float | None = None


@dataclass(slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    raw_text: str | None = None
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    compression_ratio: float | None = None
    words: list[TranscriptWord] = field(default_factory=list)


@dataclass(slots=True)
class TranscriptionResult:
    audio_path: str
    model_size: str
    language: str | None
    language_probability: float | None
    duration: float | None
    compute_type: str
    segments: list[TranscriptSegment]


def format_timestamp(seconds: float, always_hours: bool = True, include_millis: bool = False) -> str:
    seconds = max(0, float(seconds))
    total_millis = int(round(seconds * 1000))
    total_seconds, millis = divmod(total_millis, 1000)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if always_hours or hours:
        base = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        base = f"{minutes:02d}:{secs:02d}"

    if include_millis:
        return f"{base}.{millis:03d}"
    return base


def format_srt_timestamp(seconds: float) -> str:
    return format_timestamp(seconds, always_hours=True, include_millis=True).replace(".", ",")
