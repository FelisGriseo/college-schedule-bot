from aiogram import BaseMiddleware


class AppContextMiddleware(BaseMiddleware):
    def __init__(self, db, schedule, settings) -> None:
        self.db = db
        self.schedule = schedule
        self.settings = settings

    async def __call__(self, handler, event, data):
        data["db"] = self.db
        data["schedule"] = self.schedule
        data["settings"] = self.settings
        return await handler(event, data)
