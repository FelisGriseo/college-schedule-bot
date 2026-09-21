import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    channel_id: int | None
    channel_username: str | None
    database_url: str
    schedule_file: Path
    output_schedule_file: Path
    timezone: str
    api_id: int | None
    api_hash: str | None
    session_name: str
    ocr_backend: str
    ocr_enabled: bool

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_TOKEN", os.getenv("BOT_TOKEN", "")).strip()
        if not token:
            raise ValueError("TELEGRAM_TOKEN (or BOT_TOKEN) is required in .env")

        raw_channel_id = os.getenv("CHANNEL_ID", "").strip()
        return cls(
            bot_token=token,
            channel_id=int(raw_channel_id) if raw_channel_id else None,
            channel_username=os.getenv("CHANNEL_USERNAME", "").strip() or None,
            database_url=os.getenv(
                "DATABASE_URL", "sqlite+aiosqlite:///./college_schedule.db"
            ),
            schedule_file=Path(
                os.getenv(
                    "BASE_SCHEDULE_FILE",
                    os.getenv("SCHEDULE_FILE", "college_schedule_2026_2027.xlsx"),
                )
            ),
            output_schedule_file=Path(
                os.getenv(
                    "OUTPUT_SCHEDULE_FILE",
                    "college_with_replacements_schedule_2026_2027.xlsx",
                )
            ),
            timezone=os.getenv("TIMEZONE", "Europe/Kyiv"),
            api_id=int(os.getenv("API_ID", "0")) or None,
            api_hash=os.getenv("API_HASH") or None,
            session_name=os.getenv("SESSION_NAME", "schedule_monitor"),
            ocr_backend=os.getenv("OCR_BACKEND", "none").lower(),
            ocr_enabled=os.getenv("OCR_ENABLED", "false").lower() == "true",
        )
