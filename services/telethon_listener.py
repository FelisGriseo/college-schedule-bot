import logging

from aiogram import Bot
from telethon import TelegramClient, events

from config import Settings
from services.replacement_processor import process_replacement_text

logger = logging.getLogger(__name__)


async def run_user_listener(settings: Settings, session_factory, bot: Bot) -> None:
    if not settings.api_id or not settings.api_hash or not settings.channel_username:
        logger.warning(
            "Telethon listener disabled: API_ID, API_HASH and CHANNEL_USERNAME are required"
        )
        return

    client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)

    @client.on(events.NewMessage(chats=settings.channel_username))
    async def handle_new_post(event) -> None:
        text = event.message.message or ""
        if event.message.media and not text:
            logger.info("Media post %s received; OCR adapter is not configured yet", event.id)
            return
        count = await process_replacement_text(
            text=text,
            source_message_id=event.id,
            session_factory=session_factory,
            bot=bot,
        )
        if count:
            logger.info("Saved %s replacement(s) from Telegram post %s", count, event.id)

    try:
        await client.start()
        logger.info("Telethon listener is active for %s", settings.channel_username)
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
