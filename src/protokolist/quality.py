from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .segments import TranscriptionResult, TranscriptSegment, format_timestamp


@dataclass(slots=True)
class QualityWarning:
    code: str
    severity: str
    message: str
    details: dict[str, object]


@dataclass(slots=True)
class QualityReport:
    audio_duration_seconds: float | None
    last_segment_end_seconds: float | None
    recognized_coverage_percent: float | None
    segment_count: int
    warnings: list[QualityWarning]


_NORMALIZE_RE = re.compile(r"[^\wа-яА-ЯёЁ]+", re.UNICODE)


def _normalize_text(text: str) -> str:
    normalized = _NORMALIZE_RE.sub(" ", text.casefold()).strip()
    return " ".join(normalized.split())


def _last_segment_end(segments: list[TranscriptSegment]) -> float | None:
    if not segments:
        return None
    return max(segment.end for segment in segments)


def _detect_short_transcript(result: TranscriptionResult) -> QualityWarning | None:
    duration = result.duration
    last_end = _last_segment_end(result.segments)
    if duration is None or last_end is None or duration <= 0:
        return None

    gap_seconds = duration - last_end
    coverage = last_end / duration

    # A long tail with no recognized speech is often normal silence, but it must be visible.
    if gap_seconds >= 300 and coverage < 0.9:
        return QualityWarning(
            code="SHORT_TRANSCRIPT_VS_AUDIO",
            severity="warning",
            message=(
                "Последний распознанный сегмент закончился заметно раньше конца аудио. "
                "После этого может быть тишина, шум или нераспознанный участок."
            ),
            details={
                "audio_duration": format_timestamp(duration),
                "last_segment_end": format_timestamp(last_end),
                "gap_seconds": round(gap_seconds, 2),
                "recognized_coverage_percent": round(coverage * 100, 1),
            },
        )
    return None


def _detect_repeated_tail(segments: list[TranscriptSegment], min_repeats: int = 3) -> QualityWarning | None:
    if len(segments) < min_repeats:
        return None

    tail = segments[-50:]
    normalized_tail = [_normalize_text(segment.text) for segment in tail]

    last_text = normalized_tail[-1]
    if not last_text:
        return None

    repeat_count = 0
    repeated_segments: list[TranscriptSegment] = []
    for segment, normalized in zip(reversed(tail), reversed(normalized_tail), strict=True):
        if normalized != last_text:
            break
        repeat_count += 1
        repeated_segments.append(segment)

    if repeat_count < min_repeats:
        return None

    repeated_segments.reverse()
    first = repeated_segments[0]
    last = repeated_segments[-1]
    return QualityWarning(
        code="REPEATED_TAIL_PHRASE",
        severity="warning",
        message=(
            "В конце расшифровки найден повторяющийся одинаковый фрагмент. "
            "Это может быть галлюцинация Whisper на тишине или шуме."
        ),
        details={
            "repeated_text": last.text.strip(),
            "repeat_count": repeat_count,
            "start": format_timestamp(first.start),
            "end": format_timestamp(last.end),
        },
    )


def analyze_transcription_quality(result: TranscriptionResult) -> QualityReport:
    warnings: list[QualityWarning] = []

    short_transcript = _detect_short_transcript(result)
    if short_transcript:
        warnings.append(short_transcript)

    repeated_tail = _detect_repeated_tail(result.segments)
    if repeated_tail:
        warnings.append(repeated_tail)

    last_end = _last_segment_end(result.segments)
    coverage = None
    if result.duration and last_end is not None and result.duration > 0:
        coverage = min(100.0, (last_end / result.duration) * 100)

    return QualityReport(
        audio_duration_seconds=result.duration,
        last_segment_end_seconds=last_end,
        recognized_coverage_percent=coverage,
        segment_count=len(result.segments),
        warnings=warnings,
    )


def _format_warning(warning: QualityWarning) -> str:
    lines = [f"- [{warning.severity.upper()}] {warning.code}: {warning.message}"]
    for key, value in warning.details.items():
        lines.append(f"  - {key}: {value}")
    return "\n".join(lines)


def write_quality_report(report: QualityReport, output_dir: str | Path) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "meeting.quality_report.json"
    txt_path = output_dir / "meeting.quality_report.txt"

    json_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# Отчет качества распознавания Protokolist")
    lines.append("")
    lines.append(f"segments: {report.segment_count}")
    lines.append(f"audio_duration: {format_timestamp(report.audio_duration_seconds) if report.audio_duration_seconds is not None else 'unknown'}")
    lines.append(f"last_segment_end: {format_timestamp(report.last_segment_end_seconds) if report.last_segment_end_seconds is not None else 'unknown'}")
    if report.recognized_coverage_percent is None:
        lines.append("recognized_coverage_percent: unknown")
    else:
        lines.append(f"recognized_coverage_percent: {report.recognized_coverage_percent:.1f}")
    lines.append("")

    if report.warnings:
        lines.append("## Предупреждения")
        lines.append("")
        for warning in report.warnings:
            lines.append(_format_warning(warning))
            lines.append("")
        lines.append("## Как использовать")
        lines.append("")
        lines.append("Если найден повтор в конце, не считай его подтвержденной репликой без ручной проверки аудио.")
        lines.append("Если расшифровка закончилась сильно раньше аудио, проверь, была ли дальше речь или только тишина/шум.")
    else:
        lines.append("Предупреждений нет.")

    txt_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, txt_path
