from __future__ import annotations

from pathlib import Path

from .segments import TranscriptSegment, format_timestamp

DEFAULT_PARTICIPANTS = """Сергей — наладчик
Андрей Аркадьевич — лидер, босс
Вячеслав — директор
Александра — руководитель
Наталья — администратор
Андрей — механик
Андрей — кладовщик
Катерина — оператор 1С
Наталья — логист-менеджер
Алла — мастер смены
Ольга — мастер смены
Мария — мастер смены
Алексей — начальник
Дмитрий — снабженец
Иван — технолог
"""


def load_participants(path: str | Path = "participants.txt") -> str:
    path = Path(path)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return DEFAULT_PARTICIPANTS.strip()


def build_protocol_prompt(segments: list[TranscriptSegment], participants: str | None = None) -> str:
    participants = (participants or DEFAULT_PARTICIPANTS).strip()
    transcript = "\n".join(f"[{format_timestamp(seg.start)}] {seg.text}" for seg in segments)
    return f"""Ты — профессиональный корпоративный секретарь. На основе стенограммы составь структурированный протокол совещания.

Участники, которые часто встречаются на совещаниях:
{participants}

Правила обработки:
1. Диаризация: если по контексту можно понять говорящего, используй имена из списка. Если нельзя — пиши «Участник N».
2. Стенограмма: сделай тезисную стенограмму в формате [Время] Имя: краткое содержание реплики.
3. Итоги: сформируй основные темы, принятые решения и список задач.
4. Если ответственный не назван явно, но задача очевидна — пиши «Не определен».
5. Если срок не был озвучен — пиши «не определен».
6. Тон: деловой, сухой, без оценочных суждений.

Формат ответа:
# Протокол совещания

## Присутствующие

## Тезисная стенограмма

## Основные темы обсуждения

## Принятые решения

## Action Items
| Задача | Ответственный | Срок |
|---|---|---|

Стенограмма:
{transcript}
"""


def write_protocol_prompt(segments: list[TranscriptSegment], path: str | Path, participants_path: str | Path = "participants.txt") -> Path:
    path = Path(path)
    participants = load_participants(participants_path)
    prompt = build_protocol_prompt(segments, participants)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path
