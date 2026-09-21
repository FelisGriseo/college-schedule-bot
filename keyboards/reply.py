from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MENU_BUTTONS = {
    "today": "📅 Розклад на сьогодні",
    "tomorrow": "📆 Розклад на завтра",
    "week": "🗓 Розклад на тиждень",
    "change_group": "⚙️ Змінити групу",
    "notifications": "🔔 Увімкнути/Вимкнути автосповіщення",
}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_BUTTONS["today"]), KeyboardButton(text=MENU_BUTTONS["tomorrow"])],
            [KeyboardButton(text=MENU_BUTTONS["week"])],
            [KeyboardButton(text=MENU_BUTTONS["change_group"])],
            [KeyboardButton(text=MENU_BUTTONS["notifications"])],
        ],
        resize_keyboard=True,
    )
