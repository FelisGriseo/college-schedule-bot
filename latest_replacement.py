"""Download and OCR the newest post from the replacements Telegram channel."""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import RPCError

from services.ocr import _read_table
from services.replacement_parser import parse_replacements

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"У .env не задано обов'язкове значення {name}")
    return value


async def read_latest_post() -> None:
    """Authorize a user account, read one newest post, and print its OCR text."""
    api_id = int(_required_env("API_ID"))
    api_hash = _required_env("API_HASH")
    channel = os.getenv("CHANNEL_USERNAME", "replacements_xpk").strip()
    session_name = os.getenv("SESSION_NAME", "schedule_monitor").strip()

    async with TelegramClient(session_name, api_id, api_hash) as client:
        await client.start()
        entity = await client.get_entity(channel)

        # limit=1 is intentional: do not fall back to an older post.
        posts = await client.get_messages(entity, limit=1)
        if not posts:
            print("Канал не містить постів.")
            return

        post = posts[0]
        print(f"Останній пост: {post.id} ({post.date:%Y-%m-%d %H:%M:%S %Z})")
        if post.message:
            print(f"Опис: {post.message}")

        if not post.photo:
            print("Останній пост не містить фото для OCR.")
            return

        image_bytes = await client.download_media(post, file=bytes)
        if not image_bytes:
            print("Не вдалося завантажити фото з останнього поста.")
            return

        print("\nЗапускаю EasyOCR, це може тривати кілька хвилин...", flush=True)
        ocr_text = _read_table(image_bytes)
        if not ocr_text:
            # Some Telegram images have faint table text; retry before reporting failure.
            print("Перший OCR-варіант порожній, повторюю з нижчим порогом...", flush=True)
            ocr_text = _read_table(image_bytes, confidence_threshold=0.05)

        print("\nРозпізнаний текст таблиці:")
        print(ocr_text or "OCR не розпізнав текст.")

        replacements = parse_replacements(ocr_text, default_date=post.date.date())
        groups = sorted({replacement.group_name for replacement in replacements})
        if groups:
            print(f"\nВизначені групи: {', '.join(groups)}")
        else:
            print("\nНомер групи в OCR-тексті не знайдено.")


def main() -> None:
    try:
        asyncio.run(read_latest_post())
    except (ValueError, RPCError, OSError) as error:
        print(f"Помилка отримання останнього поста: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()