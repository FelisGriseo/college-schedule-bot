from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Replacement, User


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
    user.group_name = group_name
    await session.commit()


async def toggle_notifications(session: AsyncSession, telegram_id: int) -> bool:
    user = await get_or_create_user(session, telegram_id)
    user.notifications_enabled = not user.notifications_enabled
    await session.commit()
    return user.notifications_enabled


async def upsert_replacement(session: AsyncSession, values: dict) -> Replacement:
    statement = insert(Replacement).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=["replacement_date", "group_name", "pair_number"],
        set_={key: statement.excluded[key] for key in (
            "new_subject", "teacher", "room", "note", "source_message_id", "source_text"
        )},
    ).returning(Replacement)
    replacement = (await session.execute(statement)).scalar_one()
    await session.commit()
    return replacement


async def get_replacements(
    session: AsyncSession, group_name: str, start: date, end: date
) -> list[Replacement]:
    result = await session.scalars(
        select(Replacement).where(
            Replacement.group_name == group_name,
            Replacement.replacement_date >= start,
            Replacement.replacement_date <= end,
        )
    )
    return list(result)
