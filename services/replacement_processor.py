from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select

from database.crud import upsert_replacement
from database.models import User
from services.replacement_parser import ParsedReplacement, parse_replacements


async def process_replacement_text(
    text: str,
    source_message_id: int | None,
    session_factory,
    bot: Bot,
) -> int:
    parsed = parse_replacements(text)
    if not parsed:
        return 0

    async with session_factory() as session:
        for replacement in parsed:
            await _save_replacement(session, replacement, source_message_id, text)
            await _notify_users(session, bot, replacement)
    return len(parsed)


async def _save_replacement(session, replacement: ParsedReplacement, message_id: int | None, text: str) -> None:
    await upsert_replacement(session, {
        "replacement_date": replacement.replacement_date,
        "group_name": replacement.group_name,
        "pair_number": replacement.pair_number,
        "new_subject": replacement.new_subject,
        "teacher": replacement.teacher,
        "room": replacement.room,
        "note": replacement.note,
        "source_message_id": message_id,
        "source_text": text,
    })


async def _notify_users(session, bot: Bot, replacement: ParsedReplacement) -> None:
    users = await session.scalars(select(User).where(
        User.group_name == replacement.group_name,
        User.notifications_enabled.is_(True),
    ))
    notification = (
        f"🔔 Нова заміна на {replacement.replacement_date:%d.%m.%Y}, "
        f"{replacement.pair_number} пара для {replacement.group_name}: "
        f"{replacement.new_subject or replacement.note or 'оновлено'}"
    )
    for user in users:
        try:
            await bot.send_message(user.telegram_id, notification)
        except TelegramAPIError:
            continue
