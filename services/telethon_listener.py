import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot
from telethon import TelegramClient, events

from config import Settings
from services.ocr import extract_table_text
from services.replacement_processor import process_replacement_text

logger = logging.getLogger(__name__)
BACKFILL_LOG = Path(__file__).resolve().parent.parent / "replacement_log.txt"


async def run_user_listener(settings: Settings, session_factory, bot: Bot, schedule) -> None:
    if not settings.api_id or not settings.api_hash or not settings.channel_username:
        logger.warning(
            "Telethon listener disabled: API_ID, API_HASH and CHANNEL_USERNAME are required"
        )
        return

    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)

    @client.on(events.NewMessage(chats=settings.channel_username))
    async def handle_new_post(event) -> None:
        text = await _post_text(client, event.message, settings)
        if event.message.media and not text:
            logger.warning("Telegram post %s produced no OCR text", event.id)
        elif event.message.media:
            logger.info(
                "Telegram post %s OCR preview: %s",
                event.id,
                text[:500].replace("\n", " | "),
            )
        count = await process_replacement_text(
            text=text,
            source_message_id=event.id,
            session_factory=session_factory,
            bot=bot,
            default_date=event.message.date.date(),
            schedule=schedule,
        )
        if count:
            logger.info("Saved %s replacement(s) from Telegram post %s", count, event.id)

    try:
        await client.start()
        channel = await client.get_entity(settings.channel_username)
        await _backfill_history(client, channel, settings, session_factory, bot, schedule)
        logger.info("Telethon listener is active for %s", settings.channel_username)
        await client.run_until_disconnected()
    finally:
        await client.disconnect()


async def _backfill_history(client, channel, settings, session_factory, bot, schedule) -> None:
    if settings.backfill_days == 0:
        return

    cutoff = datetime.now(ZoneInfo(settings.timezone)) - timedelta(days=settings.backfill_days)
    scanned = 0
    saved = 0
    processed_replacement_posts = 0
    async for message in client.iter_messages(channel):
        if message.date < cutoff:
            break
        if not message.media:
            continue
        if processed_replacement_posts >= 2:
            break
        scanned += 1
        text = await _post_text(client, message, settings)
        if not text:
            logger.warning("History post %s produced no OCR text", message.id)
        else:
            logger.info(
                "History post %s OCR preview: %s",
                message.id,
                text[:500].replace("\n", " | "),
            )
        before = saved
        imported = await process_replacement_text(
            text=text,
            source_message_id=message.id,
            session_factory=session_factory,
            bot=bot,
            notify=False,
            default_date=message.date.date(),
            schedule=schedule,
        )
        saved += imported
        if imported:
            processed_replacement_posts += 1
        if saved == before:
            logger.warning(
                "History post %s OCR text produced no replacement rows", message.id
            )
        with BACKFILL_LOG.open("a", encoding="utf-8") as log_file:
            log_file.write(
                f"[backfill] Пост: {message.id} | Дата поста: {message.date:%d.%m.%Y} | "
                f"Розпізнано замін: {imported} | Усього імпортовано: {saved}\n"
            )
    logger.info(
        "History backfill finished: scanned %s posts, imported %s replacements",
        scanned,
        saved,
    )
    with BACKFILL_LOG.open("a", encoding="utf-8") as log_file:
        log_file.write(
            f"[backfill-summary] Перевірено постів: {scanned} | "
            f"Імпортовано замін: {saved}\n"
        )


async def _post_text(client, message, settings) -> str:
    caption = message.message or ""
    if not message.media:
        return caption
    ocr_text = await extract_table_text(client, message, settings.ocr_backend)
    if caption and ocr_text:
        return f"{caption}\n{ocr_text}"
    return caption or ocr_text
