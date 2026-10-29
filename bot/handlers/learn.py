import logging
import re

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot import llm, logic, pronounce, repo
from bot.clock import today
from bot.db import Session
from bot.keyboards import (BTN_QUIZ, BTN_STATS, BTN_TEXT, BTN_TODAY, MENU_BUTTONS, AnswerCb, KnownCb,
                           known_button, known_kb, main_menu, next_question_kb, options_kb)

router = Router()
log = logging.getLogger(__name__)

MAX_LOOKUP_WORDS = 5


@router.message(CommandStart())
async def start(message: Message):
    async with Session() as s:
        await repo.get_or_create_user(s, message.from_user.id)
    await message.answer(
        "Привет! Я помогу учить английские слова.\n\n"
        f"<b>Как это работает.</b> В первый день даю {logic.START_WORDS} новых слов. Каждый следующий день "
        f"повторяешь их и получаешь ещё {logic.STEP_WORDS}. Когда наберётся {logic.CYCLE_MAX}, начинаем "
        "новый цикл с другими словами. Одно и то же слово как новое я не выдам дважды. "
        "Если слово уже знаешь, нажми «Знаю», и я заменю его.\n\n"
        f"<b>Чтение.</b> «{BTN_TEXT}» пришлёт короткий текст на английском. Непонятное слово просто "
        "напиши мне, и я покажу транскрипцию, произношение и перевод.\n\n"
        "Напоминание приходит в 10:00, поменять: /remind 19",
        reply_markup=main_menu,
    )


@router.message(Command("today"))
@router.message(F.text == BTN_TODAY)
async def today_words(message: Message):
    async with Session() as s:
        user = await repo.get_or_create_user(s, message.from_user.id)
        words = await repo.todays_words(s, user, today())
        await repo.touch(s, user, today())
        cycle = user.cycle
    if not words:
        await message.answer("Слова в словаре закончились 🎉 Попроси администратора добавить новые.")
        return
    new = [w for w in words if w.is_new]
    old = [w for w in words if not w.is_new]
    parts = [f"<b>Цикл {cycle}, слов сегодня: {len(words)}</b>"]
    if new:
        parts.append("🆕 Новые:\n" + "\n".join(f"<b>{w.en}</b> — {w.ru}" for w in new))
    if old:
        parts.append("🔁 Повторяем:\n" + "\n".join(f"<b>{w.en}</b> — {w.ru}" for w in old))
    parts.append("Прочитай и запомни. Знакомое слово убери кнопкой ниже.")
    await message.answer("\n\n".join(parts), reply_markup=known_kb(words))


@router.callback_query(KnownCb.filter())
async def on_known(call: CallbackQuery, callback_data: KnownCb):
    async with Session() as s:
        user = await repo.get_or_create_user(s, call.from_user.id)
        replacement = await repo.mark_known(s, user, callback_data.uw, today())

    rows = [row for row in call.message.reply_markup.inline_keyboard if row[0].callback_data != call.data]
    if replacement:
        rows.append([known_button(replacement.user_word_id, replacement.en)])
    await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=rows) if rows else None)

    if replacement:
        await call.message.answer(f"Заменил. Новое слово: <b>{replacement.en}</b> — {replacement.ru}")
    await call.answer("Убрал из списка")


@router.message(Command("text"))
@router.message(F.text == BTN_TEXT)
async def reading_text(message: Message):
    if not llm.enabled():
        await message.answer("Тексты генерирует ИИ, а ключ LLM_API_KEY не настроен.")
        return
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        text = await llm.reading_text()
    except Exception:
        log.exception("reading text generation failed")
        await message.answer("Не получилось сгенерировать текст, попробуй позже.")
        return
    await message.answer(text + "\n\n✍️ Напиши непонятные слова через запятую, покажу произношение.")


async def send_question(message: Message, user_id: int):
    async with Session() as s:
        user = await repo.get_or_create_user(s, user_id)
        q = await repo.next_question(s, user)
    if q is None:
        await message.answer("Сначала возьми слова: " + BTN_TODAY)
        return
    await message.answer(f"Как переводится <b>{q.en}</b>?", reply_markup=options_kb(q.user_word_id, q.options))


@router.message(Command("quiz"))
@router.message(F.text == BTN_QUIZ)
async def quiz(message: Message):
    await send_question(message, message.from_user.id)


@router.callback_query(F.data == "quiz_next")
async def quiz_next(call: CallbackQuery):
    await call.answer()
    await send_question(call.message, call.from_user.id)


@router.callback_query(AnswerCb.filter())
async def on_answer(call: CallbackQuery, callback_data: AnswerCb):
    buttons = [b for row in call.message.reply_markup.inline_keyboard for b in row]
    chosen = buttons[callback_data.i].text
    async with Session() as s:
        result = await repo.answer(s, call.from_user.id, callback_data.uw, chosen)
    if result is None:
        await call.answer("Вопрос устарел")
        return
    correct, word = result
    verdict = "✅ Верно!" if correct else f"❌ Неверно. Правильно: <b>{word.ru}</b>"
    await call.message.edit_text(f"<b>{word.en}</b>\n{verdict}", reply_markup=next_question_kb())
    await call.answer()


@router.message(Command("stats"))
@router.message(F.text == BTN_STATS)
async def stats(message: Message):
    async with Session() as s:
        user = await repo.get_or_create_user(s, message.from_user.id)
        st = await repo.stats(s, user, today())
    await message.answer(
        "📊 Твой прогресс\n\n"
        f"Всего слов пройдено: {st.total}\n"
        f"Из них уже знал: {st.known}\n"
        f"Текущий цикл: {st.cycle} ({st.cycle_size} из {logic.CYCLE_MAX} слов)\n"
        f"Дней подряд: {st.streak} 🔥\n"
        f"Осталось в словаре: {st.left_in_dictionary}"
    )


@router.message(Command("remind"))
async def remind(message: Message):
    arg = (message.text.split(maxsplit=1)[1:] or [""])[0].strip()
    async with Session() as s:
        user = await repo.get_or_create_user(s, message.from_user.id)
        if arg == "off":
            user.remind_hour = None
            reply = "Напоминания выключены."
        elif arg.isdigit() and 0 <= int(arg) <= 23:
            user.remind_hour = int(arg)
            reply = f"Буду напоминать каждый день в {int(arg):02d}:00."
        else:
            reply = "Укажи час от 0 до 23, например /remind 19, или /remind off"
        await s.commit()
    await message.answer(reply)


@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(MENU_BUTTONS))
async def pronounce_words(message: Message):
    items = [w.strip() for w in re.split(r"[,;\n]+", message.text) if w.strip()]
    if not items or not all(re.fullmatch(r"[A-Za-z' -]{1,40}", w) for w in items):
        await message.answer("Напиши английское слово или несколько через запятую.")
        return
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    for w in items[:MAX_LOOKUP_WORDS]:
        p = await pronounce.lookup(w)
        async with Session() as s:
            known = await repo.find_word(s, p.word)
        await message.answer(pronounce.format_card(p, known.ru if known else None))
        if p.audio_url:
            try:
                await message.answer_audio(p.audio_url, title=p.word)
            except Exception:
                log.warning("audio send failed for %r", p.word)
