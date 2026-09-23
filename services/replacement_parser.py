import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

from services.text_utils import normalize_group_name


@dataclass(frozen=True)
class ParsedReplacement:
    replacement_date: date
    group_name: str
    pair_number: int
    new_subject: str | None
    teacher: str | None
    room: str | None
    note: str | None


DATE_RE = re.compile(r"(?:дата|date)\s*[:=-]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", re.IGNORECASE)
TEXT_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(січня|лютого|березня|квітня|травня|червня|"
    r"липня|серпня|вересня|жовтня|листопада|грудня)\s+(20\d{2})\b",
    re.IGNORECASE,
)
GROUP_RE = re.compile(r"(?:група|группа|group)\s*[:=-]\s*([A-Za-zА-Яа-яІіЇїЄє0-9-]+)", re.IGNORECASE)
TABLE_GROUP_RE = re.compile(r"\b([A-Za-zА-Яа-яІіЇїЄєҐґ]{2,4}[-\s]+\d{3})\b")
TABLE_PAIR_RE = re.compile(r"^(\d{1,2})\s*(?:[-–]|\s)\s*(\d{1,2})$")
PAIR_RE = re.compile(r"(?:пара|пары|pair)\s*[:№#-]*\s*(\d+)", re.IGNORECASE)
FIELD_RE = {
    "new_subject": re.compile(r"(?:новий предмет|предмет|subject)\s*[:=-]\s*(.+)", re.IGNORECASE),
    "teacher": re.compile(r"(?:викладач|преподаватель|teacher)\s*[:=-]\s*(.+)", re.IGNORECASE),
    "room": re.compile(r"(?:кабінет|кабинет|аудиторія|ауд\.|room)\s*[:=-]\s*(.+)", re.IGNORECASE),
}


def _value(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1).splitlines()[0].strip() if match else None


def _parse_date(value: str) -> date:
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported replacement date: {value}")


def _find_replacement_date(text: str, default_date: date | None) -> date | None:
    labelled_date = _value(DATE_RE, text)
    if labelled_date:
        return _parse_date(labelled_date)
    match = TEXT_DATE_RE.search(text)
    if match:
        months = {
            "січня": 1, "лютого": 2, "березня": 3, "квітня": 4,
            "травня": 5, "червня": 6, "липня": 7, "серпня": 8,
            "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
        }
        return date(int(match.group(3)), months[match.group(2).lower()], int(match.group(1)))
    return default_date


_normalize_group_name = normalize_group_name


def _clean_ocr_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    replacements = {
        "Іромадянська": "Громадянська",
        "Іромадянське": "Громадянське",
        "Громадянська освиа": "Громадянська освіта",
        "Громадянська освiта": "Громадянська освіта",
        "Украінська": "Українська",
        "Фізнка": "Фізика",
        "Математнка": "Математика",
    }
    return replacements.get(value, value)


def _looks_like_subject(value: str) -> bool:
    subject_words = (
        "освіта", "мова", "матем", "фізик", "істор", "географ", "хім",
        "машинне", "архітект", "програм", "економ", "менедж", "культура",
        "механік", "технолог", "взаємозамін", "автомобіл", "конструюван",
    )
    lowered = value.lower()
    return any(word in lowered for word in subject_words)


def parse_replacements(text: str, default_date: date | None = None) -> list[ParsedReplacement]:
    """Parse a labelled replacement post. OCR/LLM adapters can call this after producing text."""
    if not text:
        return []
    has_replacement_marker = bool(re.search(
        r"заміна|замена|replacement|скасовано|відміна", text, re.IGNORECASE
    ))
    parsed_date = _find_replacement_date(text, default_date)
    group_name = _value(GROUP_RE, text)
    pair_number = _value(PAIR_RE, text)
    if group_name and pair_number and parsed_date and has_replacement_marker:
        return [_build_replacement(parsed_date, group_name, pair_number, text)]

    if parsed_date is None:
        return []
    return _parse_table_replacements(text, parsed_date)


def _build_replacement(
    replacement_date: date, group_name: str, pair_number: str, text: str
) -> ParsedReplacement:
    subject = _value(FIELD_RE["new_subject"], text)
    note = "скасовано" if re.search(r"скасовано|відміна", text, re.IGNORECASE) else None
    return ParsedReplacement(
        replacement_date=replacement_date,
        group_name=group_name,
        pair_number=int(pair_number),
        new_subject=subject,
        teacher=_value(FIELD_RE["teacher"], text),
        room=_value(FIELD_RE["room"], text),
        note=note,
    )


def _parse_table_replacements(text: str, replacement_date: date) -> list[ParsedReplacement]:
    results: list[ParsedReplacement] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        group_match = TABLE_GROUP_RE.search(line)
        pair_match = re.search(r"\b(\d{1,2})\s*(?:[-–]|\s)\s*\d{1,2}\b", line)
        if not group_match or not pair_match:
            continue

        columns = [_clean_ocr_value(part) for part in re.split(r"\s*\|\s*", line)]
        group = normalize_group_name(group_match.group(1))
        group_index = next(
            (i for i, value in enumerate(columns) if group == _normalize_group_name(value)),
            None,
        )
        if group_index is None:
            continue
        pair_index = next(
            (i for i in range(group_index + 1, len(columns))
             if TABLE_PAIR_RE.fullmatch(columns[i])),
            None,
        )
        if pair_index is None:
            continue
        pair_number = int(TABLE_PAIR_RE.match(columns[pair_index]).group(1))
        data = columns[pair_index + 1:]
        if len(data) < 3 or any("група" in value.lower() and "виход" in value.lower() for value in data):
            continue

        # Columns after the pair are: replaced person, subject, teacher, room.
        # Empty cells must be preserved because the replaced-person field is optional.
        if len(data) >= 4:
            _, subject, teacher, room = data[:4]
        elif _looks_like_subject(data[1]):
            _, subject, teacher, room = data[0], data[1], "", data[2]
        else:
            subject, teacher, room = data[:3]
        if TABLE_PAIR_RE.fullmatch(subject):
            continue
        if subject.lower() in {"предмет", "предмети"} or teacher.lower() in {"викладач", "викладачі"}:
            continue
        room = room.replace(" ", "")
        if not subject:
            continue
        results.append(ParsedReplacement(
            replacement_date=replacement_date,
            group_name=group,
            pair_number=pair_number,
            new_subject=subject,
            teacher=teacher,
            room=room,
            note=None,
        ))
    flattened = _parse_flattened_table(text, replacement_date)
    return flattened if len(flattened) > len(results) else results


def _parse_flattened_table(text: str, replacement_date: date) -> list[ParsedReplacement]:
    columns = [_clean_ocr_value(value) for value in re.split(r"\s*\|\s*", text.replace("\n", " | "))]
    group_positions = [
        index for index, value in enumerate(columns)
        if TABLE_GROUP_RE.fullmatch(value.replace(" ", "-"))
    ]
    results: list[ParsedReplacement] = []
    for position, group_index in enumerate(group_positions):
        group = normalize_group_name(columns[group_index])
        end = group_positions[position + 1] if position + 1 < len(group_positions) else len(columns)
        pair_index = next(
            (index for index in range(group_index + 1, end) if TABLE_PAIR_RE.fullmatch(columns[index])),
            None,
        )
        if pair_index is None:
            continue
        pair_number = int(TABLE_PAIR_RE.match(columns[pair_index]).group(1))
        data = columns[pair_index + 1:end]
        if len(data) < 3:
            continue
        if len(data) >= 4:
            _, subject, teacher, room = data[:4]
        elif _looks_like_subject(data[1]):
            _, subject, teacher, room = data[0], data[1], "", data[2]
        else:
            subject, teacher, room = data[:3]
        if not subject or TABLE_PAIR_RE.fullmatch(subject):
            continue
        results.append(ParsedReplacement(
            replacement_date=replacement_date,
            group_name=group,
            pair_number=pair_number,
            new_subject=subject,
            teacher=teacher,
            room=room.replace(" ", ""),
            note=None,
        ))
    return results


async def extract_text_from_media(_message) -> str:
    """Extension point for OCR (Tesseract/EasyOCR) or an LLM vision API."""
    return ""
