import logging
from dataclasses import replace
from datetime import date
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select

from database.crud import upsert_replacement
from database.models import User
from services.replacement_parser import ParsedReplacement, parse_replacements
from services.text_utils import normalize_group_name

logger = logging.getLogger(__name__)
REPLACEMENT_LOG = Path(__file__).resolve().parent.parent / "replacement_log.txt"


def _log_parsed_replacement(replacement: ParsedReplacement, status: str, source_message_id: int | None, text: str) -> None:
    line = (
        f"[{status}] Дата: {replacement.replacement_date:%d.%m.%Y} | "
        f"Група: {replacement.group_name} | Пара: {replacement.pair_number}-"
        f"{replacement.pair_number + 1} | Предмет: "
        f"{replacement.new_subject or replacement.note or '-'} | "
        f"Викладач: {replacement.teacher or '-'} | Аудиторія: "
        f"{replacement.room or '-'} | Повідомлення: {source_message_id or '-'}"
    )
    with REPLACEMENT_LOG.open("a", encoding="utf-8") as fp:
        fp.write(line + "\n")
        fp.write(f"source_text={text[:400].replace(chr(10), ' | ')}\n")
        fp.write("-" * 80 + "\n")


async def process_replacement_text(
    text: str,
    source_message_id: int | None,
    session_factory,
    bot: Bot,
    notify: bool = True,
    default_date: date | None = None,
    schedule=None,
) -> int:
    parsed = parse_replacements(text, default_date=default_date)
    if not parsed:
        return 0

    async with session_factory() as session:
        for replacement in parsed:
            resolved_group, match_status, candidates = _resolve_group(replacement.group_name, schedule)
            if resolved_group is None:
                logger.warning(
                    '[unmatched-group] raw="%s" normalized="%s" candidates=%s',
                    replacement.group_name,
                    normalize_group_name(replacement.group_name),
                    candidates,
                )
                resolved_group = normalize_group_name(replacement.group_name)
            stored_replacement = replace(replacement, group_name=resolved_group)
            _, is_latest = await _save_replacement(
                session, stored_replacement, source_message_id, text, match_status
            )
            if not is_latest:
                logger.info(
                    "Skipped stale replacement: date=%s group=%s pair=%s source_message_id=%s",
                    replacement.replacement_date,
                    replacement.group_name,
                    replacement.pair_number,
                    source_message_id,
                )
                _log_parsed_replacement(replacement, "stale", source_message_id, text)
                continue
            logger.info(
                "Replacement parsed: date=%s group=%s pair=%s subject=%s teacher=%s room=%s",
                replacement.replacement_date,
                replacement.group_name,
                replacement.pair_number,
                replacement.new_subject or replacement.note or "cancelled",
                replacement.teacher or "-",
                replacement.room or "-",
            )
            _log_parsed_replacement(replacement, "parsed", source_message_id, text)
            if notify:
                await _notify_users(session, bot, replacement)
    return len(parsed)


def _resolve_group(group_name: str, schedule) -> tuple[str | None, str, list[str]]:
    if schedule is None:
        return normalize_group_name(group_name), "matched", []
    return schedule.resolve_group_name(group_name)


async def _save_replacement(
    session, replacement: ParsedReplacement, message_id: int | None, text: str, match_status: str
):
    return await upsert_replacement(session, {
        "replacement_date": replacement.replacement_date,
        "group_name": replacement.group_name,
        "pair_number": replacement.pair_number,
        "new_subject": replacement.new_subject,
        "teacher": replacement.teacher,
        "room": replacement.room,
        "note": replacement.note,
        "source_message_id": message_id,
        "source_text": text,
        "match_status": match_status,
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
