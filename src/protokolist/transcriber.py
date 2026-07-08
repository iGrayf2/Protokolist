from __future__ import annotations

from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel

from .cleanup import load_dictionary
from .segments import TranscriptionResult, TranscriptSegment, TranscriptWord

ProgressCallback = Callable[[str], None]


def _build_initial_prompt() -> str | None:
    dictionary = load_dictionary()
    preferred_terms = dictionary.get("preferred_terms", [])
    if not preferred_terms:
        return None
    return "В записи могут встречаться термины: " + ", ".join(preferred_terms)


def transcribe_audio(
    audio_path: str | Path,
    output_dir: str | Path | None = None,
    model_size: str = "large-v3",
    language: str = "ru",
    compute_type: str = "int8",
    device: str = "cpu",
    cpu_threads: int = 0,
    num_workers: int = 1,
    progress: ProgressCallback | None = None,
) -> TranscriptionResult:
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    output_dir = Path(output_dir) if output_dir else audio_path.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    def log(message: str) -> None:
        if progress:
            progress(message)

    log(f"Loading Whisper model: {model_size} ({device}, {compute_type})")
    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
        num_workers=num_workers,
    )

    initial_prompt = _build_initial_prompt()
    log(f"Transcribing: {audio_path.name}")
    raw_segments, info = model.transcribe(
        str(audio_path),
        language=language or None,
        task="transcribe",
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 700,
            "speech_pad_ms": 400,
        },
        beam_size=10,
        best_of=10,
        patience=1.2,
        temperature=[0.0, 0.2, 0.4],
        condition_on_previous_text=True,
        word_timestamps=True,
        initial_prompt=initial_prompt,
    )

    language_probability = getattr(info, "language_probability", None)
    if info.language:
        if language_probability is None:
            log(f"Detected language: {info.language}")
        else:
            log(f"Detected language: {info.language} ({language_probability:.2f})")

    duration = getattr(info, "duration", None)
    if duration:
        log(f"Audio duration: {duration / 60:.1f} min")

    segments: list[TranscriptSegment] = []
    for index, segment in enumerate(raw_segments, start=1):
        text = segment.text.strip()
        if not text:
            continue

        words: list[TranscriptWord] = []
        for word in segment.words or []:
            words.append(
                TranscriptWord(
                    start=getattr(word, "start", None),
                    end=getattr(word, "end", None),
                    word=getattr(word, "word", "").strip(),
                    probability=getattr(word, "probability", None),
                )
            )

        segments.append(
            TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=text,
                raw_text=text,
                avg_logprob=getattr(segment, "avg_logprob", None),
                no_speech_prob=getattr(segment, "no_speech_prob", None),
                compression_ratio=getattr(segment, "compression_ratio", None),
                words=words,
            )
        )
        if index % 10 == 0:
            if duration:
                percent = min(100.0, (segment.end / duration) * 100)
                log(f"Transcribed: {segment.end / 60:.1f}/{duration / 60:.1f} min ({percent:.0f}%), segments: {index}")
            else:
                log(f"Processed segments: {index}")

    log(f"Done. Segments: {len(segments)}")
    return TranscriptionResult(
        audio_path=str(audio_path),
        model_size=model_size,
        language=info.language,
        language_probability=language_probability,
        duration=duration,
        compute_type=compute_type,
        segments=segments,
    )
