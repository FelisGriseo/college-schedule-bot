from dataclasses import dataclass
from datetime import date

from database.models import Replacement
from services.excel_parser import ScheduleItem


@dataclass(frozen=True)
class DisplayItem:
    pair_number: int
    pair_label: str
    pair_time: str
    text: str
    subgroup: str
    lesson_type: str


def merge_schedule(
    base_items: list[ScheduleItem], replacements: list[Replacement]
) -> list[DisplayItem]:
    replacement_by_pair = {item.pair_number: item for item in replacements}
    result: list[DisplayItem] = []
    base_pair_numbers = {item.pair_number for item in base_items}
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
            details = [item.subject]
            if item.teacher:
                details.append(item.teacher)
            if item.room:
                details.append(f"ауд. {item.room}")
            text = " | ".join(details)
            if item.subgroup != "Вся група":
                text += f" | {item.subgroup}"
        result.append(DisplayItem(
            item.pair_number,
            item.pair_label,
            item.pair_time,
            text,
            item.subgroup,
            item.lesson_type,
        ))
    for replacement in replacements:
        if replacement.pair_number in base_pair_numbers:
            continue
        if replacement.note == "скасовано" or not replacement.new_subject:
            text = "❌ Пара скасована"
        else:
            text = f"🔄 ЗАМІНА: {replacement.new_subject}"
            if replacement.room:
                text += f" (ауд. {replacement.room}"
                if replacement.teacher:
                    text += f", {replacement.teacher}"
                text += ")"
        result.append(DisplayItem(
            replacement.pair_number,
            f"{replacement.pair_number}-{replacement.pair_number + 1}",
            "",
            text,
            "Вся група",
            "",
        ))
    result.sort(key=lambda item: item.pair_number)
    return result


def format_schedule(group: str, target: date, items: list[DisplayItem]) -> str:
    week_type = "чисельник" if _is_numerator(target) else "знаменник"
    title = (
        f"📋 <b>Розклад для групи: {group}</b>\n"
        f"🔸 <b>Тиждень: {week_type}</b>\n"
        f"📅 <b>{target.strftime('%d.%m.%Y')}</b>"
    )
    if not items:
        return f"{title}\n\nЗанять не знайдено."
    lines = [title, ""]
    for item in items:
        lines.append(f"<b>{item.pair_label or item.pair_number}. {item.pair_time}</b>")
        lines.append(f"<b>{item.text.split(' | ')[0]}</b>")
        details = item.text.split(" | ")[1:]
        if details:
            lines.append(f"🎓 {details[0]}")
        if len(details) > 1:
            lines.append(f"📍 {' | '.join(details[1:])}")
        if item.lesson_type:
            lines.append(f"🧪 {item.lesson_type}")
        lines.append("➖➖➖➖➖➖➖➖➖➖")
    return "\n".join(lines)


def _is_numerator(target: date) -> bool:
    from services.excel_parser import _week_type_for_date

    return _week_type_for_date(target) == "numerator"
