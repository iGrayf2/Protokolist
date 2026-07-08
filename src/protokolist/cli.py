from __future__ import annotations

import argparse
from pathlib import Path

from .exporters import write_docx, write_srt, write_txt
from .protocol_prompt import write_protocol_prompt
from .transcriber import transcribe_audio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe meeting audio with Faster-Whisper")
    parser.add_argument("audio", help="Path to audio or video file")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--language", default="ru")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--compute-type", default="int8")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    audio_path = Path(args.audio)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    segments = transcribe_audio(
        audio_path=audio_path,
        output_dir=output_dir,
        model_size=args.model,
        language=args.language,
        compute_type=args.compute_type,
        progress=print,
    )

    stem = audio_path.stem
    txt_path = write_txt(segments, output_dir / f"{stem}.txt")
    srt_path = write_srt(segments, output_dir / f"{stem}.srt")
    docx_path = write_docx(segments, output_dir / f"{stem}.docx")
    prompt_path = write_protocol_prompt(segments, output_dir / f"{stem}_protocol_prompt.md")

    print("\nFiles created:")
    for path in [txt_path, srt_path, docx_path, prompt_path]:
        print(f"- {path.resolve()}")


if __name__ == "__main__":
    main()
