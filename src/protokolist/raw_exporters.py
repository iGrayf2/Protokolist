from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .segments import TranscriptionResult, format_timestamp


SCHEMA_VERSION = 1


def _result_to_dict(result: TranscriptionResult) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audio_path": result.audio_path,
        "model_size": result.model_size,
        "language": result.language,
        "language_probability": result.language_probability,
        "duration": result.duration,
        "compute_type": result.compute_type,
        "segments": [asdict(segment) for segment in result.segments],
    }


def write_raw_json(result: TranscriptionResult, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def write_raw_txt(result: TranscriptionResult, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        file.write("# Сырая расшифровка Protokolist\n\n")
        file.write(f"audio_path: {result.audio_path}\n")
        file.write(f"model_size: {result.model_size}\n")
        file.write(f"language: {result.language}\n")
        file.write(f"language_probability: {result.language_probability}\n")
        file.write(f"duration: {result.duration}\n")
        file.write(f"compute_type: {result.compute_type}\n\n")
        for seg in result.segments:
            start = format_timestamp(seg.start, include_millis=True)
            end = format_timestamp(seg.end, include_millis=True)
            file.write(f"[{start} --> {end}] {seg.raw_text or seg.text}\n")
    return path
