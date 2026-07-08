from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class AudioPreprocessError(RuntimeError):
    """Raised when audio preprocessing cannot be completed."""


def _require_ffmpeg() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise AudioPreprocessError("ffmpeg не найден. Установи: sudo apt install -y ffmpeg")
    return ffmpeg_path


def prepare_audio_for_whisper(
    input_path: str | Path,
    output_dir: str | Path,
    output_name: str = "prepared_audio.wav",
) -> Path:
    """Convert input audio/video to a stable mono 16 kHz WAV for Whisper.

    The original source file is never modified. The prepared WAV is written
    into the meeting artifacts directory and is safe to pass to Faster-Whisper.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    ffmpeg_path = _require_ffmpeg()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]

    result = subprocess.run(command, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "unknown ffmpeg error").strip()
        raise AudioPreprocessError(f"ffmpeg не смог подготовить аудио: {details}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise AudioPreprocessError(f"ffmpeg не создал корректный WAV: {output_path}")

    return output_path
