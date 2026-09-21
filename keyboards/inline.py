from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def course_keyboard(courses: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.button(text=f"Курс {course}", callback_data=f"course:{course}")
    builder.adjust(2)
    return builder.as_markup()


def group_keyboard(groups: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for group in groups:
        builder.button(text=group, callback_data=f"group:{group}")
    builder.adjust(2)
    return builder.as_markup()
