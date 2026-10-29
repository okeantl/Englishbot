import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot import repo
from bot.config import settings
from bot.db import Base, Session, engine
from bot.handlers import admin, learn
from bot.reminders import reminders_loop


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as s:
        added = await repo.seed_words(s)
    logging.info("words seeded: %s", added)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_routers(admin.router, learn.router)

    task = asyncio.create_task(reminders_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
