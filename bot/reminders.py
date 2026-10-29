import asyncio
import logging

from aiogram import Bot
from sqlalchemy import or_, select

from bot.clock import now
from bot.db import Session, User
from bot.keyboards import BTN_TODAY

log = logging.getLogger(__name__)


async def reminders_loop(bot: Bot) -> None:
    while True:
        try:
            await send_due(bot)
        except Exception:
            log.exception("reminders iteration failed")
        await asyncio.sleep(60)


async def send_due(bot: Bot) -> None:
    current = now()
    async with Session() as s:
        users = list(await s.scalars(select(User).where(
            User.remind_hour == current.hour,
            or_(User.reminded_on.is_(None), User.reminded_on < current.date()),
        )))
        for user in users:
            try:
                await bot.send_message(user.id, f"Время учить слова! Жми «{BTN_TODAY}» 📚")
            except Exception:
                log.warning("reminder to %s failed", user.id)
            user.reminded_on = current.date()
        await s.commit()
