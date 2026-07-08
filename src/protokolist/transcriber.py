from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from faster_whisper import WhisperModel

from .segments import TranscriptSegment

ProgressCallback = Callable[[str], None]


def transcribe_audio(
    audio_path: str | Path,
    output_dir: str | Path | None = None,
    model_size: str = "small",
    language: str = "ru",
    compute_type: str = "int8",
    progress: ProgressCallback | None = None,
) -> list[TranscriptSegment]:
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    output_dir = Path(output_dir) if output_dir else audio_path.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    def log(message: str) -> None:
        if progress:
            progress(message)

    log(f"Loading Whisper model: {model_size}")
    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type=compute_type,
        cpu_threads=0,
        num_workers=1,
    )

    log(f"Transcribing: {audio_path.name}")
    raw_segments, info = model.transcribe(
        str(audio_path),
        language=language or None,
        vad_filter=True,
        beam_size=5,
        word_timestamps=False,
    )

    log(f"Detected language: {info.language} ({info.language_probability:.2f})")
    segments: list[TranscriptSegment] = []
    for index, segment in enumerate(raw_segments, start=1):
        text = segment.text.strip()
        if not text:
            continue
        segments.append(TranscriptSegment(start=segment.start, end=segment.end, text=text))
        if index % 10 == 0:
            log(f"Processed segments: {index}")

    log(f"Done. Segments: {len(segments)}")
    return segments


def plain_text(segments: Iterable[TranscriptSegment]) -> str:
    lines: list[str] = []
    for seg in segments:
        lines.append(seg.text)
    return "\n".join(lines).strip() + "\n"
