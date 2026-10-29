import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select

from bot import repo
from bot.config import settings
from bot.db import Session, User, Word

router = Router()
router.message.filter(F.from_user.func(lambda u: settings.is_admin(u.id, u.username)))
log = logging.getLogger(__name__)


def _args(message: Message) -> str:
    return (message.text.split(maxsplit=1)[1:] or [""])[0]


@router.message(Command("admin"))
async def admin_stats(message: Message):
    async with Session() as s:
        users = await s.scalar(select(func.count()).select_from(User))
        words = await s.scalar(select(func.count()).select_from(Word))
    await message.answer(
        f"Пользователей: {users}\nСлов в словаре: {words}\n\n"
        "Добавить слова: /addwords и строки вида <code>word - перевод</code>\n"
        "Рассылка: /broadcast текст"
    )


@router.message(Command("addwords"))
async def add_words(message: Message):
    items = []
    for line in _args(message).splitlines():
        if " - " in line:
            en, ru = line.split(" - ", 1)
            items.append({"en": en, "ru": ru})
    if not items:
        await message.answer("Формат:\n/addwords\napple - яблоко\nriver - река")
        return
    async with Session() as s:
        added = await repo.add_words(s, items)
    await message.answer(f"Добавлено новых слов: {added} из {len(items)}")


@router.message(Command("broadcast"))
async def broadcast(message: Message, bot: Bot):
    text = _args(message)
    if not text:
        await message.answer("Использование: /broadcast текст")
        return
    async with Session() as s:
        ids = list(await s.scalars(select(User.id)))
    sent = 0
    for uid in ids:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            log.warning("broadcast to %s failed", uid)
        await asyncio.sleep(0.05)
    await message.answer(f"Отправлено: {sent} из {len(ids)}")
