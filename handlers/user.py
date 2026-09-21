from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.crud import get_or_create_user, get_replacements, set_user_group, toggle_notifications
from database.models import User
from keyboards.inline import course_keyboard, group_keyboard
from keyboards.reply import MENU_BUTTONS, main_menu
from services.schedule_merger import format_schedule, merge_schedule

router = Router(name="user")


def _group_required(user: User | None) -> str | None:
    return user.group_name if user else None


async def show_group_picker(message: Message, schedule, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Оберіть курс:", reply_markup=course_keyboard(list(schedule.groups_by_course())))


@router.message(CommandStart())
async def start(message: Message, db, schedule, state: FSMContext) -> None:
    async with db.session_factory() as session:
        user = await get_or_create_user(session, message.from_user.id)
    if user.group_name:
        await message.answer(
            f"Ваша збережена група: {user.group_name}",
            reply_markup=main_menu(),
        )
        return
    await show_group_picker(message, schedule, state)


@router.callback_query(F.data.startswith("course:"))
async def choose_course(callback: CallbackQuery, schedule, state: FSMContext) -> None:
    course = callback.data.split(":", 1)[1]
    await state.update_data(course=course)
    await callback.message.edit_text(
        f"Курс {course}. Оберіть групу:",
        reply_markup=group_keyboard(schedule.groups_by_course().get(course, [])),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("group:"))
async def choose_group(callback: CallbackQuery, db, state: FSMContext) -> None:
    group = callback.data.split(":", 1)[1]
    async with db.session_factory() as session:
        await set_user_group(session, callback.from_user.id, group)
    await state.clear()
    await callback.message.answer(f"Групу {group} збережено.", reply_markup=main_menu())
    await callback.answer()


async def _send_day(message: Message, db, schedule, target: date) -> None:
    async with db.session_factory() as session:
        user = await get_or_create_user(session, message.from_user.id)
        if not user.group_name:
            await message.answer("Спочатку оберіть групу через /start.")
            return
        replacements = await get_replacements(session, user.group_name, target, target)
    base = schedule.for_group_and_date(user.group_name, target)
    await message.answer(format_schedule(user.group_name, target, merge_schedule(base, replacements)))


@router.message(F.text == MENU_BUTTONS["today"])
async def today(message: Message, db, schedule) -> None:
    await _send_day(message, db, schedule, datetime.now(ZoneInfo("Europe/Kyiv")).date())


@router.message(F.text == MENU_BUTTONS["tomorrow"])
async def tomorrow(message: Message, db, schedule) -> None:
    await _send_day(
        message, db, schedule, datetime.now(ZoneInfo("Europe/Kyiv")).date() + timedelta(days=1)
    )


@router.message(F.text == MENU_BUTTONS["week"])
async def week(message: Message, db, schedule) -> None:
    async with db.session_factory() as session:
        user = await get_or_create_user(session, message.from_user.id)
        if not user.group_name:
            await message.answer("Спочатку оберіть групу через /start.")
            return
        start = datetime.now(ZoneInfo("Europe/Kyiv")).date()
        replacements = await get_replacements(session, user.group_name, start, start + timedelta(days=6))
    sections = []
    by_date = {start + timedelta(days=index): [] for index in range(7)}
    for replacement in replacements:
        by_date[replacement.replacement_date].append(replacement)
    for target, day_replacements in by_date.items():
        items = merge_schedule(schedule.for_group_and_date(user.group_name, target), day_replacements)
        sections.append(format_schedule(user.group_name, target, items))
    await message.answer("\n\n".join(sections))


@router.message(F.text == MENU_BUTTONS["change_group"])
async def change_group(message: Message, schedule, state: FSMContext) -> None:
    await show_group_picker(message, schedule, state)


@router.message(F.text == MENU_BUTTONS["notifications"])
async def notifications(message: Message, db) -> None:
    async with db.session_factory() as session:
        enabled = await toggle_notifications(session, message.from_user.id)
    state = "увімкнено" if enabled else "вимкнено"
    await message.answer(f"Автосповіщення {state}.", reply_markup=main_menu())
