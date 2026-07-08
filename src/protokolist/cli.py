from __future__ import annotations

import argparse
from pathlib import Path

from .chatgpt_package import build_chatgpt_package, create_meeting_output_dir
from .cleanup import cleanup_segments
from .exporters import write_docx, write_srt, write_txt
from .raw_exporters import write_raw_json, write_raw_txt
from .transcriber import transcribe_audio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a ChatGPT-ready meeting package with Faster-Whisper")
    parser.add_argument("audio", help="Path to audio or video file")
    parser.add_argument("--model", default="large-v3", choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--language", default="ru")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--profile", default="profiles/factory_moydod.json", help="Organization profile JSON path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    audio_path = Path(args.audio)
    output_root = Path(args.output_dir)
    meeting_dir = create_meeting_output_dir(output_root, audio_path)
    artifacts_dir = meeting_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    result = transcribe_audio(
        audio_path=audio_path,
        output_dir=artifacts_dir,
        model_size=args.model,
        language=args.language,
        compute_type=args.compute_type,
        progress=print,
    )

    raw_json_path = write_raw_json(result, artifacts_dir / "meeting.raw.json")
    raw_txt_path = write_raw_txt(result, artifacts_dir / "meeting.raw.txt")

    print("Applying transcript cleanup dictionary...")
    cleaned_segments = cleanup_segments(result.segments)

    cleaned_txt_path = write_txt(cleaned_segments, artifacts_dir / "meeting.cleaned.txt")
    write_srt(cleaned_segments, artifacts_dir / "meeting.cleaned.srt")
    write_docx(cleaned_segments, artifacts_dir / "meeting.cleaned.docx")

    print("Building ChatGPT package...")
    package_dir, zip_path = build_chatgpt_package(
        result=result,
        cleaned_segments=cleaned_segments,
        raw_json_path=raw_json_path,
        raw_txt_path=raw_txt_path,
        cleaned_txt_path=cleaned_txt_path,
        meeting_dir=meeting_dir,
        profile_path=args.profile,
    )

    print("\nDone. Main outputs:")
    print(f"- Meeting folder: {meeting_dir.resolve()}")
    print(f"- ChatGPT package: {package_dir.resolve()}")
    print(f"- Zip: {zip_path.resolve()}")
    print("\nUpload the zip to ChatGPT and write: Выполни CHATGPT_TASK.md")


if __name__ == "__main__":
    main()
