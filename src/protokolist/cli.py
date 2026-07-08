from __future__ import annotations

import argparse
from pathlib import Path

from .cleanup import cleanup_segments
from .exporters import write_docx, write_srt, write_txt
from .protocol_prompt import write_protocol_prompt
from .raw_exporters import write_raw_json, write_raw_txt
from .transcriber import transcribe_audio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe meeting audio with Faster-Whisper")
    parser.add_argument("audio", help="Path to audio or video file")
    parser.add_argument("--model", default="large-v3", choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--language", default="ru")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--compute-type", default="int8")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    audio_path = Path(args.audio)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = transcribe_audio(
        audio_path=audio_path,
        output_dir=output_dir,
        model_size=args.model,
        language=args.language,
        compute_type=args.compute_type,
        progress=print,
    )

    stem = audio_path.stem
    raw_json_path = write_raw_json(result, output_dir / f"{stem}.raw.json")
    raw_txt_path = write_raw_txt(result, output_dir / f"{stem}.raw.txt")

    print("Applying transcript cleanup dictionary...")
    cleaned_segments = cleanup_segments(result.segments)

    txt_path = write_txt(cleaned_segments, output_dir / f"{stem}.cleaned.txt")
    srt_path = write_srt(cleaned_segments, output_dir / f"{stem}.cleaned.srt")
    docx_path = write_docx(cleaned_segments, output_dir / f"{stem}.cleaned.docx")
    prompt_path = write_protocol_prompt(cleaned_segments, output_dir / f"{stem}_protocol_prompt.md")

    print("\nFiles created:")
    for path in [raw_json_path, raw_txt_path, txt_path, srt_path, docx_path, prompt_path]:
        print(f"- {path.resolve()}")


if __name__ == "__main__":
    main()
