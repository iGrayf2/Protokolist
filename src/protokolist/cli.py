from __future__ import annotations

import argparse
import importlib.metadata
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

from .audio_preprocess import prepare_audio_for_whisper
from .chatgpt_package import build_chatgpt_package, create_meeting_output_dir
from .cleanup import cleanup_segments
from .exporters import write_docx, write_srt, write_txt
from .quality import analyze_transcription_quality, write_quality_report
from .raw_exporters import write_raw_json, write_raw_txt
from .transcriber import transcribe_audio

APP_VERSION = "0.3.0"


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

    def warn(self, message: str) -> None:
        self.line(f"  ! {message}")

    def fail(self, message: str) -> None:
        self.line(f"  ✘ {message}")

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


def _safe_distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _check_ffmpeg(printer: CliPrinter) -> bool:
    path = shutil.which("ffmpeg")
    if path:
        printer.ok(f"ffmpeg найден: {path}")
        return True
    printer.fail("ffmpeg не найден. Установи: sudo apt install -y ffmpeg")
    return False


def _print_run_header(args: argparse.Namespace, audio_path: Path, printer: CliPrinter) -> None:
    printer.title(f"Protokolist CLI {APP_VERSION}")
    printer.info(f"Input:        {audio_path}")
    printer.info(f"Output root:  {Path(args.output_dir)}")
    printer.info(f"Profile:      {args.profile}")
    printer.info(f"Model:        {args.model}")
    printer.info(f"Language:     {args.language}")
    printer.info(f"Device:       {args.device}")
    printer.info(f"Compute type: {args.compute_type}")
    printer.info(f"CPU threads:  {'auto' if args.cpu_threads == 0 else args.cpu_threads}")
    printer.info(f"Preprocess:   {'off' if args.no_preprocess else 'ffmpeg mono WAV 16 kHz'}")
    printer.info(f"Safe mode:    {'on' if args.safe_mode else 'off'}")


def process_audio(args: argparse.Namespace) -> int:
    printer = CliPrinter(quiet=args.quiet)
    audio_path = Path(args.audio)
    if not audio_path.exists():
        printer.error(f"Файл не найден: {audio_path}")
        return 2

    started_at = time.monotonic()
    _print_run_header(args, audio_path, printer)

    total_stages = 8

    try:
        printer.stage(1, total_stages, "Подготовка папки встречи")
        output_root = Path(args.output_dir)
        meeting_dir = create_meeting_output_dir(output_root, audio_path)
        artifacts_dir = meeting_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        printer.ok(f"Meeting folder: {meeting_dir.resolve()}")

        printer.stage(2, total_stages, "Предобработка аудио через ffmpeg")
        if args.no_preprocess:
            whisper_audio_path = audio_path
            printer.warn("Предобработка отключена, Whisper получит исходный файл")
            _check_ffmpeg(printer)
        else:
            whisper_audio_path = prepare_audio_for_whisper(audio_path, artifacts_dir)
            printer.ok(str(whisper_audio_path.resolve()))

        printer.stage(3, total_stages, "Распознавание аудио через Faster-Whisper")
        result = transcribe_audio(
            audio_path=whisper_audio_path,
            output_dir=artifacts_dir,
            model_size=args.model,
            language=args.language,
            compute_type=args.compute_type,
            device=args.device,
            cpu_threads=args.cpu_threads,
            num_workers=args.num_workers,
            safe_mode=args.safe_mode,
            progress=printer.info,
        )
        if whisper_audio_path != audio_path:
            result = replace(result, audio_path=f"{audio_path} -> {whisper_audio_path}")
        printer.ok(f"Распознано сегментов: {len(result.segments)}")

        printer.stage(4, total_stages, "Проверка качества распознавания")
        quality_report = analyze_transcription_quality(result)
        quality_json_path, quality_txt_path = write_quality_report(quality_report, artifacts_dir)
        if quality_report.warnings:
            for warning in quality_report.warnings:
                printer.warn(f"{warning.code}: {warning.message}")
        else:
            printer.ok("Критичных предупреждений не найдено")
        printer.ok(str(quality_txt_path.resolve()))
        printer.ok(str(quality_json_path.resolve()))

        printer.stage(5, total_stages, "Сохранение RAW-артефактов")
        raw_json_path = write_raw_json(result, artifacts_dir / "meeting.raw.json")
        raw_txt_path = write_raw_txt(result, artifacts_dir / "meeting.raw.txt")
        printer.ok(str(raw_json_path.resolve()))
        printer.ok(str(raw_txt_path.resolve()))

        printer.stage(6, total_stages, "Мягкая словарная очистка")
        cleaned_segments = cleanup_segments(result.segments)
        printer.ok("Очистка выполнена. RAW не изменялся")

        printer.stage(7, total_stages, "Экспорт TXT/SRT/DOCX")
        cleaned_txt_path = write_txt(cleaned_segments, artifacts_dir / "meeting.cleaned.txt")
        srt_path = write_srt(cleaned_segments, artifacts_dir / "meeting.cleaned.srt")
        docx_path = write_docx(cleaned_segments, artifacts_dir / "meeting.cleaned.docx")
        printer.ok(str(cleaned_txt_path.resolve()))
        printer.ok(str(srt_path.resolve()))
        printer.ok(str(docx_path.resolve()))

        printer.stage(8, total_stages, "Сборка CHATGPT_PACKAGE и ZIP")
        package_dir, zip_path = build_chatgpt_package(
            result=result,
            cleaned_segments=cleaned_segments,
            raw_json_path=raw_json_path,
            raw_txt_path=raw_txt_path,
            cleaned_txt_path=cleaned_txt_path,
            meeting_dir=meeting_dir,
            profile_path=args.profile,
            quality_report_txt_path=quality_txt_path,
            quality_report_json_path=quality_json_path,
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


def run_doctor(args: argparse.Namespace) -> int:
    printer = CliPrinter()
    root = Path.cwd()
    checks_failed = 0

    printer.title(f"Protokolist doctor {APP_VERSION}")

    if sys.version_info >= (3, 10):
        printer.ok(f"Python {sys.version.split()[0]}")
    else:
        printer.fail(f"Python {sys.version.split()[0]} слишком старый")
        checks_failed += 1

    if not _check_ffmpeg(printer):
        checks_failed += 1

    faster_whisper_version = _safe_distribution_version("faster-whisper")
    if faster_whisper_version:
        printer.ok(f"faster-whisper {faster_whisper_version}")
    else:
        printer.fail("faster-whisper не установлен")
        checks_failed += 1

    docx_version = _safe_distribution_version("python-docx")
    if docx_version:
        printer.ok(f"python-docx {docx_version}")
    else:
        printer.fail("python-docx не установлен")
        checks_failed += 1

    for folder_name in ["input", "output", "logs", "models", "cache"]:
        folder = root / folder_name
        if folder.exists() and folder.is_dir():
            printer.ok(f"Папка есть: {folder_name}/")
        else:
            printer.warn(f"Папка отсутствует, будет нужна: {folder_name}/")

    profile_path = Path(args.profile)
    if profile_path.exists():
        printer.ok(f"Профиль найден: {profile_path}")
    else:
        printer.fail(f"Профиль не найден: {profile_path}")
        checks_failed += 1

    dictionary_path = Path(args.dictionary)
    if dictionary_path.exists():
        printer.ok(f"Словарь найден: {dictionary_path}")
    else:
        printer.warn(f"Словарь не найден: {dictionary_path}")

    usage = shutil.disk_usage(root)
    free_gb = usage.free / 1024 / 1024 / 1024
    if free_gb >= 20:
        printer.ok(f"Свободно на диске: {free_gb:.1f} ГБ")
    else:
        printer.warn(f"Свободно на диске мало: {free_gb:.1f} ГБ")

    if shutil.which("nvidia-smi"):
        printer.ok("nvidia-smi найден")
    else:
        printer.warn("nvidia-smi не найден, рабочий режим по умолчанию: CPU")

    printer.title("Итог")
    if checks_failed:
        printer.fail(f"Есть критичные проблемы: {checks_failed}")
        return 1
    printer.ok("Окружение выглядит рабочим")
    return 0


def show_version(_: argparse.Namespace) -> int:
    print(f"Protokolist {APP_VERSION}")
    return 0


def add_process_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("audio", help="Путь к аудио или видео файлу")
    parser.add_argument("--model", default="large-v3", choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--language", default="ru")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    parser.add_argument("--cpu-threads", type=int, default=0, help="0 = auto")
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--profile", default="profiles/factory_moydod.json", help="Путь к профилю предприятия")
    parser.add_argument("--no-preprocess", action="store_true", help="Отключить ffmpeg-подготовку WAV и передать исходный файл в Whisper")
    parser.add_argument("--safe-mode", action="store_true", help="Снизить риск повторов/галлюцинаций на шумных записях")
    parser.add_argument("--quiet", action="store_true", help="Минимальный вывод")
    parser.set_defaults(func=process_audio)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="protokolist",
        description="CLI-only генератор ChatGPT-пакета из записи производственного совещания",
    )
    subparsers = parser.add_subparsers(dest="command")

    process = subparsers.add_parser("process", help="Обработать аудио/видео и собрать ChatGPT ZIP")
    add_process_arguments(process)

    doctor = subparsers.add_parser("doctor", help="Проверить окружение перед обработкой")
    doctor.add_argument("--profile", default="profiles/factory_moydod.json")
    doctor.add_argument("--dictionary", default="config/dictionary.json")
    doctor.set_defaults(func=run_doctor)

    hardware = subparsers.add_parser("hardware", help="Собрать отчет по железу Ubuntu-машины")
    hardware.add_argument("--output", default="protokolist_hardware.txt")
    hardware.set_defaults(func=collect_hardware)

    version = subparsers.add_parser("version", help="Показать версию Protokolist")
    version.set_defaults(func=show_version)

    return parser


def main() -> None:
    parser = build_parser()

    # Main UX: `protokolist input/meeting.mp3` without a required `process` word.
    if len(sys.argv) > 1 and sys.argv[1] not in {"process", "doctor", "hardware", "version", "-h", "--help"}:
        args = parser.parse_args(["process", *sys.argv[1:]])
    else:
        args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        raise SystemExit(2)

    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
