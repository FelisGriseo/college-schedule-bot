import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "course", "group", "day", "pair_number", "pair_time", "subject", "teacher", "room"
}


def _parse_pair_number(value: object) -> int:
    """Accept Excel values such as 1, 1.0 and a lesson range like 1-2."""
    text = str(value).strip()
    match = re.match(r"^(\d+)(?:\s*[-–]\s*\d+)?(?:\.0)?$", text)
    if not match:
        raise ValueError(f"Unsupported pair_number value in Excel: {value!r}")
    return int(match.group(1))


@dataclass(frozen=True)
class ScheduleItem:
    course: str
    group: str
    day: str
    pair_number: int
    pair_time: str
    subject: str
    teacher: str
    room: str


class ExcelSchedule:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.items: list[ScheduleItem] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(
                f"Schedule file not found: {self.path}. Put college_schedule_2026_2027.xlsx in the project root."
            )
        frame = pd.read_excel(self.path, sheet_name="Parsed_Schedule")
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"Parsed_Schedule is missing columns: {', '.join(sorted(missing))}")

        for row in frame.fillna("").to_dict(orient="records"):
            if not str(row["group"]).strip() or not str(row["subject"]).strip():
                continue
            self.items.append(ScheduleItem(
                course=str(row["course"]).strip(),
                group=str(row["group"]).strip(),
                day=str(row["day"]).strip(),
                pair_number=_parse_pair_number(row["pair_number"]),
                pair_time=str(row["pair_time"]).strip(),
                subject=str(row["subject"]).strip(),
                teacher=str(row["teacher"]).strip(),
                room=str(row["room"]).strip(),
            ))

    def groups_by_course(self) -> dict[str, list[str]]:
        result: dict[str, set[str]] = {}
        for item in self.items:
            result.setdefault(item.course, set()).add(item.group)
        return {course: sorted(groups) for course, groups in sorted(result.items())}

    def for_group_and_date(self, group: str, target: date) -> list[ScheduleItem]:
        day_names = {
            0: ("понеділок", "понедельник", "monday"),
            1: ("вівторок", "вторник", "tuesday"),
            2: ("середа", "среда", "wednesday"),
            3: ("четвер", "четверг", "thursday"),
            4: ("п’ятниця", "п'ятниця", "пятница", "friday"),
            5: ("субота", "суббота", "saturday"),
            6: ("неділя", "воскресенье", "sunday"),
        }
        aliases = day_names[target.weekday()]
        return sorted(
            [item for item in self.items if item.group == group and item.day.strip().lower() in aliases],
            key=lambda item: item.pair_number,
        )
