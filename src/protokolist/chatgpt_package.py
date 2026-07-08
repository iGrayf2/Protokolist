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
        "package_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audio_path": result.audio_path,
        "audio_duration_seconds": result.duration,
        "language": result.language,
        "language_probability": result.language_probability,
        "model_size": result.model_size,
        "compute_type": result.compute_type,
        "profile": profile,
    }


def _build_task_md(profile: dict[str, Any], has_quality_report: bool = False) -> str:
    profile_name = profile.get("profile_name", "factory_moydod") if profile else "factory_moydod"
    quality_file = "- `meeting.quality_report.txt` — отчет качества распознавания: короткая расшифровка относительно аудио, повторы в конце, возможные галлюцинации Whisper.\n" if has_quality_report else ""
    quality_step = "\nПеред анализом проверь `meeting.quality_report.txt`, если файл есть. Если там указаны повторы в конце или короткая расшифровка относительно аудио, учитывай это в разделе контроля качества и не считай подозрительные повторы подтвержденными репликами.\n" if has_quality_report else ""
    return f"""# CHATGPT_TASK.md

Ты получил пакет Protokolist для обработки длинного производственного совещания.

Этот пакет подготовлен специально для ChatGPT. Работай не как обычный пересказчик, а как строгий корпоративный секретарь. Главный принцип: лучше написать `не определено`, чем красиво додумать.

## Главный результат

Итогом работы должен быть **файл Microsoft Word `.docx`**, а не только текстовый ответ в чате.

Создай и приложи Word-документ с именем:

```text
protokol_soveshchaniya.docx
```

В ответе в чате дай только короткое сообщение и ссылку на созданный `.docx` файл. Если в текущей среде невозможно создать файл Word, тогда честно напиши об этом и только после этого выведи результат в Markdown.

## Файлы в пакете

- `meeting_context.json` — профиль предприятия, участники, роли, термины, правила обработки.
- `meeting.raw.json` — главный источник правды: сырые сегменты Whisper, таймкоды, слова и метаданные.
- `meeting.raw.txt` — сырой текст для быстрого чтения.
- `meeting.cleaned.txt` — текст после мягкой словарной очистки.
{quality_file}
## Профиль

Используй профиль: `{profile_name}`.

Профиль — это только справочник возможных людей и терминов. Он НЕ является доказательством присутствия человека на встрече.

Особенно важно:

- не придумывай говорящих;
- не назначай роль `Ведущий`, если в тексте нет прямого подтверждения, что человек именно ведет совещание;
- не пиши `Ведущий, вероятно ...`; такой формат запрещен;
- не используй слова `вероятно`, `скорее всего`, `предположительно` в имени говорящего;
- если говорящий не установлен точно, пиши `Неопознанный участник N`;
- если участник сам представился фразой вроде `меня зовут ...`, это можно считать прямым основанием для имени в этой реплике;
- если несколько людей представились одним именем, например Андрей, различай их как `Андрей 1`, `Андрей 2`, `Андрей 3` только при необходимости, но не назначай им роли без прямого основания;
- если имя совпадает у нескольких людей, например Андрей или Наталья, указывай роль только при наличии прямого текстового основания;
- мастера смен работают посменно;
- всего мастеров смен шесть: Алла, Ольга, Мария, Юлия, Людмила, Светлана;
- на одном совещании обычно присутствуют только три мастера смены из шести;
- не считай автоматически, что присутствовали все шесть;
- решения, задачи, сроки и ответственных извлекай только из текста.
{quality_step}
## Запрет на вероятностные подписи

В итоговой стенограмме запрещены такие подписи:

```text
Ведущий, вероятно Андрей Аркадьевич:
Александра / Саша, вероятно:
Катерина / неопознанный участник:
Ведущий / неопознанный участник:
```

Вместо этого используй один из двух вариантов:

```text
Катерина:
Неопознанный участник 1:
```

Если уверенности в имени нет — выбирай `Неопознанный участник N`.

## Алгоритм работы

Выполни обработку последовательно. Не перескакивай к финальному протоколу, пока не сделаешь анализ.

### Шаг 1. Изучи контекст

Прочитай `meeting_context.json`.

Определи:

- что это за предприятие;
- какие роли и участники известны;
- какие термины важны;
- какие правила определения участников нужно учитывать.

### Шаг 2. Построй карту встречи

На основе `meeting.raw.json` и `meeting.cleaned.txt` определи:

- кто точно присутствует по прямым фразам или явным обращениям;
- кого определить нельзя;
- какие темы обсуждаются;
- какие фрагменты плохо распознаны.

Не составляй список `вероятно присутствующих`. Если участник не подтвержден — помести его в `не определено / требуется проверка`.

### Шаг 3. Исправь ошибки распознавания

Исправь только очевидные ошибки Whisper.

Сохраняй:

- цифры;
- даты;
- артикулы;
- названия документов;
- названия систем;
- производственные термины;
- смысл реплик.

Если фрагмент непонятен — пометь его как `[неразборчиво]`, а не выдумывай.

### Шаг 4. Определи говорящих

Разбей разговор на реплики.

Правила определения говорящих:

1. Имя можно ставить только при прямом основании: самопредставление, явное обращение, явно продолженная реплика того же человека.
2. Нельзя назначать говорящего только по роли, стилю речи, теме реплики или профилю предприятия.
3. Нельзя писать `вероятно`, `скорее всего`, `предположительно` рядом с именем говорящего.
4. Если говорящий неясен, используй `Неопознанный участник N`.
5. Если человек говорит фразу `меня зовут Андрей`, но таких Андреев несколько, подпиши как `Андрей 1`, `Андрей 2`, `Андрей 3` без роли.
6. Не меняй смысл реплик.
7. Сохраняй таймкоды.

Формат:

```text
[00:00:00] Имя или Неопознанный участник N: суть реплики.
```

### Шаг 5. Сделай осмысленную стенограмму

Сделай читаемую, но честную стенограмму.

Не превращай стенограмму в художественный пересказ. Сохраняй деловой смысл.

### Шаг 6. Составь протокол

Сформируй:

- подтвержденные присутствующие;
- неопознанные участники;
- основные темы;
- ход обсуждения;
- принятые решения;
- нерешенные вопросы;
- спорные моменты.

Не указывай `ведущего`, если это прямо не зафиксировано в тексте. Если кто-то просто задает вопросы, это не делает его ведущим.

### Шаг 7. Извлеки Action Items

Сделай таблицу:

| Задача | Ответственный | Срок | Основание / таймкод | Уверенность |
|---|---|---|---|---|

Жесткое правило: Action Item можно добавлять только если в тексте есть прямое поручение, просьба, договоренность или формулировка `надо/нужно/сделать/проверить` с понятным действием.

Нельзя превращать обсуждаемую проблему в задачу от себя.

Если ответственный не назван — пиши `не определен`.

Если срок не назван — пиши `не определен`.

Если прямых поручений нет, напиши: `Прямые поручения в записи не зафиксированы`.

### Шаг 8. Проведи контроль качества

В конце обязательно добавь раздел:

## Контроль качества

Укажи:

- общую уверенность;
- какие имена подтверждены прямым самопредставлением или обращением;
- какие говорящие оставлены неопознанными;
- уверенность в задачах;
- фрагменты, которые нужно проверить вручную;
- возможные ошибки распознавания;
- возможные неверные назначения говорящих;
- предупреждения из `meeting.quality_report.txt`, если файл есть.

## Структура Word-документа

Word-документ должен содержать разделы:

# Результат обработки совещания

## 1. Карта встречи

## 2. Исправленная стенограмма с говорящими

## 3. Протокол совещания

## 4. Принятые решения

## 5. Action Items

## 6. Вопросы без решения

## 7. Контроль качества

## 8. Фрагменты для ручной проверки

## Жесткие запреты

- Не выдумывай факты.
- Не назначай ведущего без прямого основания.
- Не используй формулировки `Ведущий, вероятно ...`.
- Не используй вероятностные подписи говорящих.
- Не составляй список вероятно присутствующих.
- Не назначай ответственных без основания.
- Не назначай сроки без основания.
- Не добавляй участников только потому, что они есть в профиле.
- Не превращай проблему в задачу, если в тексте не было прямого поручения.
- Не исправляй технические термины на похожие общеупотребительные слова.
- Не скрывай неуверенность.
- Не ограничивайся финальным текстом в чате, если есть возможность создать `.docx` файл.
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

4. Дождись результата.

## Главный результат

ChatGPT должен вернуть итоговый протокол как файл Word:

```text
protokol_soveshchaniya.docx
```

В чате достаточно короткого сообщения со ссылкой на созданный `.docx` файл.

## Важное правило качества

Если говорящий не подтвержден прямо, ChatGPT должен писать `Неопознанный участник N`, а не `Ведущий, вероятно ...` или другие вероятностные подписи.

## Главный файл

`CHATGPT_TASK.md` — инструкция для ChatGPT.

## Что внутри

- `meeting_context.json` — профиль предприятия и правила.
- `meeting.raw.json` — главный сырой файл.
- `meeting.raw.txt` — сырой текст.
- `meeting.cleaned.txt` — очищенный текст.
{quality}
## Важно

Для длинных совещаний около часа ChatGPT может не обработать все за один проход. Если модель попросит продолжить — напиши `продолжай`.
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

    # Extra compact transcript for quick human inspection.
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
