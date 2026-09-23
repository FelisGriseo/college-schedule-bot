from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Replacement, User
from services.replacement_parser import normalize_group_name


async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    user = await session.get(User, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def set_user_group(session: AsyncSession, telegram_id: int, group_name: str) -> None:
    user = await get_or_create_user(session, telegram_id)
    user.group_name = normalize_group_name(group_name)
    await session.commit()


async def toggle_notifications(session: AsyncSession, telegram_id: int) -> bool:
    user = await get_or_create_user(session, telegram_id)
    user.notifications_enabled = not user.notifications_enabled
    await session.commit()
    return user.notifications_enabled


async def upsert_replacement(session: AsyncSession, values: dict) -> tuple[Replacement, bool]:
    normalized_values = dict(values)
    normalized_values["group_name"] = normalize_group_name(str(values["group_name"]))
    candidates = await session.scalars(select(Replacement).where(
        Replacement.replacement_date == normalized_values["replacement_date"],
        Replacement.pair_number == normalized_values["pair_number"],
    ))
    existing = next(
        (item for item in candidates
         if normalize_group_name(item.group_name) == normalized_values["group_name"]),
        None,
    )
    incoming_message_id = normalized_values.get("source_message_id")
    if (
        existing is not None
        and incoming_message_id is not None
        and existing.source_message_id is not None
        and existing.source_message_id >= incoming_message_id
    ):
        return existing, False

    if existing is not None:
        for key, value in normalized_values.items():
            setattr(existing, key, value)
        await session.commit()
        await session.refresh(existing)
        return existing, True

    statement = insert(Replacement).values(**normalized_values)
    statement = statement.on_conflict_do_update(
        index_elements=["replacement_date", "group_name", "pair_number"],
        set_={key: statement.excluded[key] for key in (
            "new_subject", "teacher", "room", "note", "source_message_id", "source_text",
            "match_status"
        )},
    ).returning(Replacement)
    replacement = (await session.execute(statement)).scalar_one()
    await session.commit()
    return replacement, True


async def get_replacements(
    session: AsyncSession, group_name: str, start: date, end: date
) -> list[Replacement]:
    result = await session.scalars(
        select(Replacement).where(
            Replacement.replacement_date >= start,
            Replacement.replacement_date <= end,
        )
    )
    wanted_group = normalize_group_name(group_name)
    latest_by_pair: dict[int, Replacement] = {}
    for replacement in result:
        if normalize_group_name(replacement.group_name) != wanted_group:
            continue
        if replacement.match_status == "unmatched":
            continue
        current = latest_by_pair.get(replacement.pair_number)
        current_id = current.source_message_id if current else -1
        replacement_id = replacement.source_message_id or -1
        if current is None or replacement_id >= current_id:
            latest_by_pair[replacement.pair_number] = replacement
    return list(latest_by_pair.values())
