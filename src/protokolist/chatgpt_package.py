from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .prompt_pipeline import load_profile
from .segments import TranscriptionResult, TranscriptSegment, format_timestamp

PACKAGE_DIR_NAME = "CHATGPT_PACKAGE"
TASK_FILE_NAME = "CHATGPT_TASK.md"


def _safe_name(name: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_ ." else "_" for char in name).strip()
    return safe or "meeting"


def create_meeting_output_dir(output_root: str | Path, audio_path: str | Path) -> Path:
    audio_path = Path(audio_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    meeting_dir = Path(output_root) / f"{timestamp}_{_safe_name(audio_path.stem)}"
    meeting_dir.mkdir(parents=True, exist_ok=True)
    return meeting_dir


def _format_transcript(segments: list[TranscriptSegment], raw: bool = False) -> str:
    lines: list[str] = []
    for segment in segments:
        start = format_timestamp(segment.start, include_millis=True)
        end = format_timestamp(segment.end, include_millis=True)
        text = segment.raw_text if raw and segment.raw_text else segment.text
        lines.append(f"[{start} --> {end}] {text}")
    return "\n".join(lines).strip() + "\n"


def _write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _build_context(result: TranscriptionResult, profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_type": "Protokolist ChatGPT Package",
        "package_version": "1.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audio_path": result.audio_path,
        "audio_duration_seconds": result.duration,
        "language": result.language,
        "language_probability": result.language_probability,
        "model_size": result.model_size,
        "compute_type": result.compute_type,
        "target_result": "short_protocol_docx_like_reference",
        "profile": profile,
    }


def _build_task_md(profile: dict[str, Any], has_quality_report: bool = False) -> str:
    profile_name = profile.get("profile_name", "factory_moydod") if profile else "factory_moydod"
    quality_file = "- `meeting.quality_report.txt` — предупреждения качества распознавания.\n" if has_quality_report else ""
    quality_rule = "\nПеред работой проверь `meeting.quality_report.txt`. Если там есть предупреждения о повторах или короткой расшифровке, не включай подозрительные повторы в протокол как подтвержденные реплики.\n" if has_quality_report else ""
    return f"""# CHATGPT_TASK.md

Ты получил пакет Protokolist для обработки производственного совещания.

Главная задача: создать **короткий деловой протокол в Word `.docx`** строго по целевому формату. Не делай длинный аналитический отчет, карту встречи, отдельную исправленную стенограмму, контроль качества и большие пояснения в финальном документе.

## Главный результат

Создай и приложи Word-документ с именем:

```text
protokol_soveshchaniya.docx
```

В ответе в чате дай только короткое сообщение и ссылку на созданный `.docx` файл. Если Word-файл создать невозможно, честно напиши об этом и выведи тот же протокол в Markdown.

## Файлы в пакете

- `meeting_context.json` — профиль предприятия, возможные участники, роли, термины и правила.
- `meeting.raw.json` — главный источник правды: сырые сегменты Whisper, таймкоды, слова и метаданные.
- `meeting.raw.txt` — сырой текст для быстрого чтения.
- `meeting.cleaned.txt` — текст после мягкой словарной очистки.
- `meeting.cleaned_with_timestamps.txt` — очищенный текст с таймкодами.
{quality_file}
## Профиль

Используй профиль: `{profile_name}`.

Профиль — это справочник возможных людей и терминов. Он НЕ доказывает, что человек присутствовал на встрече.
{quality_rule}
## Жесткий целевой формат Word-документа

Финальный `.docx` должен содержать только эти разделы и именно в таком порядке:

1. `Протокол совещания`
2. короткая строка: `Документ составлен по доступной части стенограммы (~N минут).`
3. `Присутствующие`
4. `Тезисная стенограмма`
5. `Основные темы`
6. `Принятые решения`
7. таблица задач с колонками: `Задача`, `Ответственный`, `Срок`

Не добавляй в финальный документ разделы `Карта встречи`, `Контроль качества`, `Фрагменты для ручной проверки`, `Action Items`, `Вопросы без решения`, если пользователь прямо не попросил.

## Шаблон результата

```text
Протокол совещания
Документ составлен по доступной части стенограммы (~N минут).

Присутствующие
• Андрей Аркадьевич — ведущий совещания
• Катерина — оператор 1С
• Мария — мастер смены
• Алла — мастер смены
• Ольга — мастер смены
• Вячеслав — присутствует
• Андрей (механик/кладовщик)
• Остальные участники

Тезисная стенограмма
[00:00] Андрей Аркадьевич: Объявляет тестирование системы записи и распознавания совещаний.
[00:00:25] Андрей Аркадьевич: Просит участников назвать имена для записи голосовых образцов.
[00:01:36] Катерина: Докладывает итоги июня по складу.

Основные темы
• Тестирование системы протоколирования.
• Итоги склада за июнь.
• Пересчет остатков вязального цеха.

Принятые решения
• Продолжить тестирование записи совещаний.
• Исправить оформление таблиц.
• Исправить формулы расчета брака.

Задача | Ответственный | Срок
Исправить оформление таблиц | Катерина | не определен
Исправить формулы | Мария | не определен
```

## Правила краткости

- Делай тезисную стенограмму не дословной, а смысловой.
- Одна реплика = один короткий деловой тезис.
- Не пиши длинные абзацы.
- Если запись длинная, группируй похожие реплики и оставляй ключевые повороты обсуждения.
- Таймкоды сохраняй в формате `[00:00]` или `[00:00:25]`.
- Формулировки должны быть протокольными: `Докладывает`, `Просит`, `Подчеркивает`, `Переходит`, `Объясняет`, `Требует`, `Подтверждает`.

## Правила определения участников

- Имя ставь только при прямом основании: самопредставление, явное обращение, явно продолженная реплика того же человека.
- Если говорящий не установлен точно, пиши `Неопознанный участник N`.
- Не пиши `вероятно`, `скорее всего`, `предположительно` рядом с именем говорящего.
- Не используй подписи вида `Ведущий, вероятно Андрей Аркадьевич`.
- Не назначай роль из профиля, если в тексте нет прямого основания.
- В разделе `Присутствующие` перечисляй только подтвержденных или явно звучащих в записи людей. Остальных можно одной строкой: `Остальные участники`.

## Правила решений и задач

- В `Принятые решения` добавляй только то, что звучит как решение, требование, договоренность или явно принятое направление действий.
- В таблицу задач добавляй только прямые поручения или действия из текста.
- Если ответственный не назван — пиши `не определен`.
- Если срок не назван — пиши `не определен`.
- Таблица задач должна иметь только 3 колонки: `Задача`, `Ответственный`, `Срок`.
- Не добавляй колонки `Основание`, `Таймкод`, `Уверенность`.

## Минимальная внутренняя проверка перед выдачей

Перед созданием файла проверь молча:

- документ короткий и похож на эталон;
- нет лишних разделов;
- есть тезисная стенограмма с таймкодами;
- есть основные темы;
- есть принятые решения;
- есть таблица задач из 3 колонок;
- не выдуманы участники, ответственные и сроки;
- `1С` не превращено в `С 1`;
- технические и производственные термины сохранены.

## Жесткие запреты

- Не выдумывай факты.
- Не делай большой аналитический отчет вместо протокола.
- Не добавляй финальный раздел контроля качества.
- Не добавляй список вероятно присутствующих.
- Не назначай ведущего без прямого основания.
- Не назначай ответственных и сроки без основания.
- Не скрывай неуверенность: используй `не определен`.
"""


def _build_human_readme(meeting_name: str, has_quality_report: bool = False) -> str:
    quality = "\n- `meeting.quality_report.txt` — предупреждения о качестве распознавания.\n" if has_quality_report else ""
    return f"""# Пакет для ChatGPT

Это готовый пакет Protokolist для записи `{meeting_name}`.

## Как пользоваться

1. Открой ChatGPT.
2. Загрузи весь этот пакет или zip-архив.
3. Напиши в чат:

```text
Выполни CHATGPT_TASK.md
```

4. Получи короткий протокол совещания в Word.

## Главный результат

ChatGPT должен вернуть итоговый протокол как файл Word:

```text
protokol_soveshchaniya.docx
```

Формат результата закреплен в `CHATGPT_TASK.md`: короткий протокол, присутствующие, тезисная стенограмма, основные темы, принятые решения и таблица задач из 3 колонок.

## Что внутри

- `CHATGPT_TASK.md` — главная инструкция для ChatGPT.
- `meeting_context.json` — профиль предприятия и правила.
- `meeting.raw.json` — главный сырой файл.
- `meeting.raw.txt` — сырой текст.
- `meeting.cleaned.txt` — очищенный текст.
- `meeting.cleaned_with_timestamps.txt` — очищенный текст с таймкодами.
{quality}
"""


def build_chatgpt_package(
    result: TranscriptionResult,
    cleaned_segments: list[TranscriptSegment],
    raw_json_path: str | Path,
    raw_txt_path: str | Path,
    cleaned_txt_path: str | Path,
    meeting_dir: str | Path,
    profile_path: str | Path = "profiles/factory_moydod.json",
    quality_report_txt_path: str | Path | None = None,
    quality_report_json_path: str | Path | None = None,
    zip_name_source_path: str | Path | None = None,
) -> tuple[Path, Path]:
    meeting_dir = Path(meeting_dir)
    package_dir = meeting_dir / PACKAGE_DIR_NAME
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    profile = load_profile(profile_path)
    context = _build_context(result, profile)
    has_quality_report = quality_report_txt_path is not None and Path(quality_report_txt_path).exists()
    display_source_path = Path(zip_name_source_path) if zip_name_source_path else Path(result.audio_path)

    shutil.copy2(raw_json_path, package_dir / "meeting.raw.json")
    shutil.copy2(raw_txt_path, package_dir / "meeting.raw.txt")
    shutil.copy2(cleaned_txt_path, package_dir / "meeting.cleaned.txt")

    if quality_report_txt_path and Path(quality_report_txt_path).exists():
        shutil.copy2(quality_report_txt_path, package_dir / "meeting.quality_report.txt")
    if quality_report_json_path and Path(quality_report_json_path).exists():
        shutil.copy2(quality_report_json_path, package_dir / "meeting.quality_report.json")

    _write_json(package_dir / "meeting_context.json", context)
    (package_dir / TASK_FILE_NAME).write_text(_build_task_md(profile, has_quality_report=has_quality_report), encoding="utf-8")
    (package_dir / "README.md").write_text(_build_human_readme(display_source_path.name, has_quality_report=has_quality_report), encoding="utf-8")
    (package_dir / "meeting.cleaned_with_timestamps.txt").write_text(
        _format_transcript(cleaned_segments, raw=False),
        encoding="utf-8",
    )

    zip_path = meeting_dir / f"{_safe_name(display_source_path.stem)}_chatgpt_package.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in package_dir.rglob("*"):
            archive.write(file, file.relative_to(meeting_dir))

    return package_dir, zip_path
