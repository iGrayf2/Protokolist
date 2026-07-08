from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .segments import TranscriptSegment, format_timestamp

DEFAULT_PROFILE_PATH = Path("profiles") / "factory_moydod.json"


def load_profile(path: str | Path = DEFAULT_PROFILE_PATH) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _format_profile(profile: dict[str, Any]) -> str:
    if not profile:
        return "Профиль предприятия не найден. Используй только данные из стенограммы."

    lines: list[str] = []
    lines.append(f"Профиль: {profile.get('profile_name', 'default')}")
    lines.append("")

    context = profile.get("organization_context", [])
    if context:
        lines.append("Контекст предприятия:")
        for item in context:
            lines.append(f"- {item}")
        lines.append("")

    participants = profile.get("participants", [])
    if participants:
        lines.append("Известные участники:")
        for participant in participants:
            lines.append(f"- {participant.get('name')} — {participant.get('role')}")
        lines.append("")

    shift_supervisors = profile.get("shift_supervisors", {})
    if shift_supervisors:
        names = ", ".join(shift_supervisors.get("names", []))
        lines.append("Мастера смен:")
        lines.append(f"- Роль: {shift_supervisors.get('role', 'мастер смены')}")
        lines.append(f"- Возможные мастера: {names}")
        lines.append(f"- Правило: {shift_supervisors.get('attendance_rule')}")
        lines.append("")

    terms = profile.get("preferred_terms", [])
    if terms:
        lines.append("Важные термины:")
        lines.append(", ".join(terms))
        lines.append("")

    rules = profile.get("processing_rules", [])
    if rules:
        lines.append("Правила обработки:")
        for rule in rules:
            lines.append(f"- {rule}")
        lines.append("")

    return "\n".join(lines).strip()


def _format_transcript(segments: list[TranscriptSegment], raw: bool = False) -> str:
    lines: list[str] = []
    for segment in segments:
        start = format_timestamp(segment.start, include_millis=True)
        end = format_timestamp(segment.end, include_millis=True)
        text = segment.raw_text if raw and segment.raw_text else segment.text
        lines.append(f"[{start} --> {end}] {text}")
    return "\n".join(lines)


def build_meeting_analysis_prompt(segments: list[TranscriptSegment], profile: dict[str, Any] | None = None) -> str:
    profile_text = _format_profile(profile or load_profile())
    transcript = _format_transcript(segments, raw=True)
    return f"""Ты анализируешь сырую расшифровку производственного совещания.

Не пиши стенограмму и не пересказывай разговор. Твоя задача — построить карту встречи для последующей обработки.

{profile_text}

Задача:
1. Определи, кто ведет совещание.
2. Определи, кто точно присутствует.
3. Определи, кто вероятно присутствует.
4. Отдельно определи мастеров смен, которые вероятно присутствуют. Помни: обычно присутствуют только три мастера из шести.
5. Укажи, кого нельзя уверенно определить.
6. Найди основные темы совещания.
7. Найди важные термины, документы, номера, даты и сокращения.
8. Найди плохо распознанные фрагменты с таймкодами.
9. Не придумывай отсутствующие данные.
10. Верни результат строго в JSON.

Формат JSON:
{{
  "host": {{"name": "", "confidence": 0.0, "evidence": ""}},
  "confirmed_participants": [{{"name": "", "role": "", "confidence": 0.0, "evidence": ""}}],
  "probable_participants": [{{"name": "", "role": "", "confidence": 0.0, "evidence": ""}}],
  "probable_shift_supervisors": [{{"name": "", "confidence": 0.0, "evidence": ""}}],
  "unknown_speakers": [{{"label": "Неопознанный участник 1", "description": "", "evidence": ""}}],
  "topics": [""],
  "terms": [""],
  "bad_fragments": [{{"time": "", "text": "", "reason": ""}}],
  "notes_for_next_step": [""]
}}

----- RAW TRANSCRIPT START -----
{transcript}
----- RAW TRANSCRIPT END -----
"""


def build_transcript_repair_prompt(segments: list[TranscriptSegment], profile: dict[str, Any] | None = None) -> str:
    profile_text = _format_profile(profile or load_profile())
    transcript = _format_transcript(segments, raw=True)
    return f"""Ты исправляешь ошибки распознавания речи в сырой стенограмме производственного совещания.

Твоя задача — сделать текст читаемее, но не менять смысл.

{profile_text}

Правила:
1. Исправляй только очевидные ошибки распознавания.
2. Сохраняй все числа, даты, артикулы, названия документов и технические термины.
3. Не добавляй факты, которых нет в сыром тексте.
4. Если фраза непонятна, оставь ее близко к оригиналу и пометь как [неразборчиво].
5. Сохраняй таймкоды каждого сегмента.
6. Не назначай говорящих на этом этапе.

Верни исправленную стенограмму в формате:
[00:00:00.000 --> 00:00:05.000] Исправленный текст

----- RAW TRANSCRIPT START -----
{transcript}
----- RAW TRANSCRIPT END -----
"""


def build_speaker_assignment_prompt(segments: list[TranscriptSegment], profile: dict[str, Any] | None = None) -> str:
    profile_text = _format_profile(profile or load_profile())
    transcript = _format_transcript(segments, raw=False)
    return f"""Ты определяешь говорящих в производственном совещании.

{profile_text}

Правила:
1. Используй имена только если есть контекст: обращение, роль, тема, последовательность разговора.
2. Если имя совпадает у нескольких людей, например Андрей или Наталья, указывай роль только если она понятна.
3. Для мастеров смен помни: обычно присутствуют только три мастера из шести, не подставляй всех подряд.
4. Если говорящий неясен, используй "Неопознанный участник N".
5. Не меняй смысл реплик.
6. Сохраняй таймкоды.

Верни результат в формате:
[00:00:00.000 --> 00:00:05.000] Имя или Неопознанный участник N: текст реплики

----- CLEANED TRANSCRIPT START -----
{transcript}
----- CLEANED TRANSCRIPT END -----
"""


def build_final_minutes_prompt(segments: list[TranscriptSegment], profile: dict[str, Any] | None = None) -> str:
    profile_text = _format_profile(profile or load_profile())
    transcript = _format_transcript(segments, raw=False)
    return f"""Ты профессиональный корпоративный секретарь.

На основе подготовленной стенограммы составь качественный документ по производственному совещанию.

{profile_text}

Требования:
1. Не придумывай факты.
2. Если ответственный не назван явно — пиши "не определен".
3. Если срок не назван — пиши "не определен".
4. Сохраняй технические термины, номера, документы и названия систем.
5. Отдельно выдели спорные или неуверенные места.
6. Тон деловой, сухой, без оценочных суждений.

Формат ответа:
# Протокол совещания

## Присутствующие

## Повестка / основные темы

## Тезисная стенограмма

## Принятые решения

## Action Items
| Задача | Ответственный | Срок | Основание / таймкод |
|---|---|---|---|

## Вопросы без решения

## Фрагменты, требующие ручной проверки

----- TRANSCRIPT START -----
{transcript}
----- TRANSCRIPT END -----
"""


def build_quality_check_prompt(segments: list[TranscriptSegment], profile: dict[str, Any] | None = None) -> str:
    profile_text = _format_profile(profile or load_profile())
    transcript = _format_transcript(segments, raw=False)
    return f"""Ты проверяющий качества стенограммы и протокола.

{profile_text}

Проверь материал и найди:
1. Возможные ошибки в именах говорящих.
2. Возможные ошибки в числах, датах, артикулах и сроках.
3. Противоречия.
4. Потерянные или сомнительные реплики.
5. Места, где модель могла додумать лишнее.
6. Фрагменты, которые нужно проверить вручную.

Верни JSON:
{{
  "overall_confidence": 0.0,
  "participants_confidence": 0.0,
  "transcript_confidence": 0.0,
  "tasks_confidence": 0.0,
  "issues": [{{"time": "", "type": "", "description": "", "severity": "low|medium|high"}}],
  "manual_review_required": true
}}

----- TRANSCRIPT START -----
{transcript}
----- TRANSCRIPT END -----
"""


def write_prompt_pipeline(
    segments: list[TranscriptSegment],
    output_dir: str | Path,
    stem: str,
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = load_profile(profile_path)

    prompts = {
        "01_meeting_analysis": build_meeting_analysis_prompt(segments, profile),
        "02_transcript_repair": build_transcript_repair_prompt(segments, profile),
        "03_speaker_assignment": build_speaker_assignment_prompt(segments, profile),
        "04_final_minutes": build_final_minutes_prompt(segments, profile),
        "05_quality_check": build_quality_check_prompt(segments, profile),
    }

    paths: list[Path] = []
    for name, content in prompts.items():
        path = output_dir / f"{stem}_{name}.md"
        path.write_text(content, encoding="utf-8")
        paths.append(path)
    return paths
