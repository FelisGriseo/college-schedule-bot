import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Settings
from database.session import Database
from handlers.dependencies import AppContextMiddleware
from handlers.user import router as user_router
from services.channel_listener import build_channel_router
from services.excel_parser import ExcelSchedule
from services.telethon_listener import run_user_listener


async def run() -> None:
    settings = Settings.from_env()
    schedule = ExcelSchedule(settings.schedule_file)
    database = Database(settings.database_url)
    await database.create_tables()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    context = AppContextMiddleware(database, schedule, settings)
    dispatcher.message.middleware(context)
    dispatcher.callback_query.middleware(context)
    dispatcher.include_router(user_router)
    dispatcher.include_router(build_channel_router(settings, database.session_factory, bot))
    telethon_task = asyncio.create_task(
        run_user_listener(settings, database.session_factory, bot)
    )

    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        telethon_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await telethon_task
        await bot.session.close()
        await database.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
