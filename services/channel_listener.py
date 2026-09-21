from aiogram import Bot, Router
from aiogram.types import Message

from config import Settings
from services.replacement_parser import extract_text_from_media, parse_replacements
from services.replacement_processor import process_replacement_text

router = Router(name="channel_listener")


def build_channel_router(settings: Settings, session_factory, bot: Bot) -> Router:
    channel_router = Router(name="channel_posts")

    @channel_router.channel_post()
    async def handle_channel_post(message: Message) -> None:
        channel_matches = (
            settings.channel_id is not None and message.chat.id == settings.channel_id
        ) or (
            settings.channel_username is not None
            and message.chat.username is not None
            and message.chat.username.lower() == settings.channel_username.lstrip("@").lower()
        )
        if (settings.channel_id is not None or settings.channel_username is not None) and not channel_matches:
            return
        text = message.text or message.caption or ""
        if message.photo and not text:
            text = await extract_text_from_media(message)
        parsed = parse_replacements(text)
        if not parsed:
            return
        await process_replacement_text(text, message.message_id, session_factory, bot)

    return channel_router
