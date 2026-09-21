from dataclasses import dataclass
from datetime import date

from database.models import Replacement
from services.excel_parser import ScheduleItem


@dataclass(frozen=True)
class DisplayItem:
    pair_number: int
    pair_time: str
    text: str


def merge_schedule(
    base_items: list[ScheduleItem], replacements: list[Replacement]
) -> list[DisplayItem]:
    replacement_by_pair = {item.pair_number: item for item in replacements}
    result: list[DisplayItem] = []
    for item in base_items:
        replacement = replacement_by_pair.get(item.pair_number)
        if replacement:
            if replacement.note == "скасовано" or not replacement.new_subject:
                text = f"❌ {item.subject} скасовано"
            else:
                text = f"🔄 ЗАМІНА: {item.subject} -> {replacement.new_subject}"
                if replacement.room:
                    text += f" (ауд. {replacement.room}"
                    if replacement.teacher:
                        text += f", {replacement.teacher}"
                    text += ")"
        else:
            text = f"{item.subject} | {item.teacher} | ауд. {item.room}"
        result.append(DisplayItem(item.pair_number, item.pair_time, text))
    return result


def format_schedule(group: str, target: date, items: list[DisplayItem]) -> str:
    title = f"📅 Розклад для {group} на {target.strftime('%d.%m.%Y')}"
    if not items:
        return f"{title}\n\nЗанять не знайдено."
    lines = [title, ""]
    lines.extend(f"{item.pair_number}. {item.pair_time} — {item.text}" for item in items)
    return "\n".join(lines)
