from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .chatgpt_package import build_chatgpt_package, create_meeting_output_dir
from .cleanup import cleanup_segments
from .exporters import write_docx, write_srt, write_txt
from .raw_exporters import write_raw_json, write_raw_txt
from .transcriber import transcribe_audio


@dataclass(slots=True)
class CliPrinter:
    quiet: bool = False

    def line(self, message: str = "") -> None:
        if not self.quiet:
            print(message, flush=True)

    def title(self, message: str) -> None:
        if self.quiet:
            return
        bar = "─" * 58
        print(f"\n{bar}\n {message}\n{bar}", flush=True)

    def stage(self, number: int, total: int, message: str) -> None:
        self.line(f"\n[{number}/{total}] {message}")

    def ok(self, message: str) -> None:
        self.line(f"  ✔ {message}")

    def info(self, message: str) -> None:
        self.line(f"  {message}")

    def error(self, message: str) -> None:
        print(f"ERROR: {message}", file=sys.stderr, flush=True)


def _format_elapsed(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _check_ffmpeg(printer: CliPrinter) -> None:
    if shutil.which("ffmpeg"):
        printer.ok("ffmpeg найден")
        return
    printer.info("ffmpeg не найден. Установи: sudo apt install -y ffmpeg")


def _print_run_header(args: argparse.Namespace, audio_path: Path, printer: CliPrinter) -> None:
    printer.title("Protokolist CLI")
    printer.info(f"Input:        {audio_path}")
    printer.info(f"Output root:  {Path(args.output_dir)}")
    printer.info(f"Profile:      {args.profile}")
    printer.info(f"Model:        {args.model}")
    printer.info(f"Language:     {args.language}")
    printer.info(f"Device:       {args.device}")
    printer.info(f"Compute type: {args.compute_type}")
    printer.info(f"CPU threads:  {'auto' if args.cpu_threads == 0 else args.cpu_threads}")


def process_audio(args: argparse.Namespace) -> int:
    printer = CliPrinter(quiet=args.quiet)
    audio_path = Path(args.audio)
    if not audio_path.exists():
        printer.error(f"Файл не найден: {audio_path}")
        return 2

    started_at = time.monotonic()
    _print_run_header(args, audio_path, printer)

    total_stages = 6

    try:
        printer.stage(1, total_stages, "Подготовка папки встречи")
        output_root = Path(args.output_dir)
        meeting_dir = create_meeting_output_dir(output_root, audio_path)
        artifacts_dir = meeting_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        printer.ok(f"Meeting folder: {meeting_dir.resolve()}")
        _check_ffmpeg(printer)

        printer.stage(2, total_stages, "Распознавание аудио через Faster-Whisper")
        result = transcribe_audio(
            audio_path=audio_path,
            output_dir=artifacts_dir,
            model_size=args.model,
            language=args.language,
            compute_type=args.compute_type,
            device=args.device,
            cpu_threads=args.cpu_threads,
            num_workers=args.num_workers,
            progress=printer.info,
        )
        printer.ok(f"Распознано сегментов: {len(result.segments)}")

        printer.stage(3, total_stages, "Сохранение RAW-артефактов")
        raw_json_path = write_raw_json(result, artifacts_dir / "meeting.raw.json")
        raw_txt_path = write_raw_txt(result, artifacts_dir / "meeting.raw.txt")
        printer.ok(str(raw_json_path.resolve()))
        printer.ok(str(raw_txt_path.resolve()))

        printer.stage(4, total_stages, "Мягкая словарная очистка")
        cleaned_segments = cleanup_segments(result.segments)
        printer.ok("Очистка выполнена. RAW не изменялся")

        printer.stage(5, total_stages, "Экспорт TXT/SRT/DOCX")
        cleaned_txt_path = write_txt(cleaned_segments, artifacts_dir / "meeting.cleaned.txt")
        srt_path = write_srt(cleaned_segments, artifacts_dir / "meeting.cleaned.srt")
        docx_path = write_docx(cleaned_segments, artifacts_dir / "meeting.cleaned.docx")
        printer.ok(str(cleaned_txt_path.resolve()))
        printer.ok(str(srt_path.resolve()))
        printer.ok(str(docx_path.resolve()))

        printer.stage(6, total_stages, "Сборка CHATGPT_PACKAGE и ZIP")
        package_dir, zip_path = build_chatgpt_package(
            result=result,
            cleaned_segments=cleaned_segments,
            raw_json_path=raw_json_path,
            raw_txt_path=raw_txt_path,
            cleaned_txt_path=cleaned_txt_path,
            meeting_dir=meeting_dir,
            profile_path=args.profile,
        )
        printer.ok(str(package_dir.resolve()))
        printer.ok(str(zip_path.resolve()))

        elapsed = _format_elapsed(time.monotonic() - started_at)
        printer.title("Готово")
        printer.info(f"Elapsed:       {elapsed}")
        printer.info(f"Meeting:       {meeting_dir.resolve()}")
        printer.info(f"ChatGPT ZIP:   {zip_path.resolve()}")
        printer.info("Дальше загрузи ZIP в ChatGPT и напиши: Выполни CHATGPT_TASK.md")
        return 0
    except KeyboardInterrupt:
        printer.error("Остановлено пользователем")
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI must show any crash clearly.
        printer.error(str(exc))
        return 1


def collect_hardware(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    commands: list[tuple[str, list[str]]] = [
        ("OS", ["bash", "-lc", "lsb_release -a 2>/dev/null || cat /etc/os-release"]),
        ("CPU", ["lscpu"]),
        ("RAM", ["free", "-h"]),
        ("DISKS", ["lsblk", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL"]),
        ("GPU/PCI", ["bash", "-lc", "lspci | grep -Ei 'vga|3d|display|nvidia|amd|intel' || true"]),
        ("NVIDIA", ["bash", "-lc", "nvidia-smi 2>/dev/null || echo 'nvidia-smi не найден'"]),
        ("USB", ["lsusb"]),
        ("FULL HW SHORT", ["bash", "-lc", "sudo lshw -short 2>/dev/null || lshw -short 2>/dev/null || echo 'lshw не найден'"]),
    ]

    parts: list[str] = []
    for title, command in commands:
        parts.append(f"=== {title} ===")
        try:
            result = subprocess.run(command, check=False, text=True, capture_output=True)
            text = result.stdout.strip() or result.stderr.strip()
            parts.append(text or "нет данных")
        except FileNotFoundError:
            parts.append(f"команда не найдена: {command[0]}")
        parts.append("")

    output_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Hardware report saved: {output_path.resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="protokolist",
        description="CLI-only генератор ChatGPT-пакета из записи производственного совещания",
    )
    subparsers = parser.add_subparsers(dest="command")

    process = subparsers.add_parser("process", help="Обработать аудио/видео и собрать ChatGPT ZIP")
    process.add_argument("audio", help="Путь к аудио или видео файлу")
    process.add_argument("--model", default="large-v3", choices=["tiny", "base", "small", "medium", "large-v3"])
    process.add_argument("--language", default="ru")
    process.add_argument("--output-dir", default="output")
    process.add_argument("--compute-type", default="int8")
    process.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    process.add_argument("--cpu-threads", type=int, default=0, help="0 = auto")
    process.add_argument("--num-workers", type=int, default=1)
    process.add_argument("--profile", default="profiles/factory_moydod.json", help="Путь к профилю предприятия")
    process.add_argument("--quiet", action="store_true", help="Минимальный вывод")
    process.set_defaults(func=process_audio)

    hardware = subparsers.add_parser("hardware", help="Собрать отчет по железу Ubuntu-машины")
    hardware.add_argument("--output", default="protokolist_hardware.txt")
    hardware.set_defaults(func=collect_hardware)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        # Backward compatibility: `python -m protokolist.cli input/meeting.mp3`.
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            args = parser.parse_args(["process", *sys.argv[1:]])
        else:
            parser.print_help()
            raise SystemExit(2)

    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
