import re
from dataclasses import dataclass
from datetime import UTC, date, datetime


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
GROUP_RE = re.compile(r"(?:група|группа|group)\s*[:=-]\s*([A-Za-zА-Яа-яІіЇїЄє0-9-]+)", re.IGNORECASE)
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


def parse_replacements(text: str) -> list[ParsedReplacement]:
    """Parse a labelled replacement post. OCR/LLM adapters can call this after producing text."""
    if not text or not re.search(
        r"заміна|замена|replacement|скасовано|відміна", text, re.IGNORECASE
    ):
        return []
    replacement_date = _value(DATE_RE, text)
    group_name = _value(GROUP_RE, text)
    pair_number = _value(PAIR_RE, text)
    if not (replacement_date and group_name and pair_number):
        return []
    subject = _value(FIELD_RE["new_subject"], text)
    note = "скасовано" if re.search(r"скасовано|відміна", text, re.IGNORECASE) else None
    return [ParsedReplacement(
        replacement_date=_parse_date(replacement_date),
        group_name=group_name,
        pair_number=int(pair_number),
        new_subject=subject,
        teacher=_value(FIELD_RE["teacher"], text),
        room=_value(FIELD_RE["room"], text),
        note=note,
    )]


async def extract_text_from_media(_message) -> str:
    """Extension point for OCR (Tesseract/EasyOCR) or an LLM vision API."""
    return ""
