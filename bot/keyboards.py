from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

BTN_TODAY = "📚 Слова на сегодня"
BTN_TEXT = "📖 Текст для чтения"
BTN_QUIZ = "🧠 Проверить себя"
BTN_STATS = "📊 Статистика"
MENU_BUTTONS = {BTN_TODAY, BTN_TEXT, BTN_QUIZ, BTN_STATS}

main_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_TODAY), KeyboardButton(text=BTN_TEXT)],
              [KeyboardButton(text=BTN_QUIZ), KeyboardButton(text=BTN_STATS)]],
    resize_keyboard=True,
)


class KnownCb(CallbackData, prefix="k"):
    uw: int


class AnswerCb(CallbackData, prefix="a"):
    uw: int
    i: int


def known_button(user_word_id: int, en: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=f"✅ Знаю «{en}»", callback_data=KnownCb(uw=user_word_id).pack())


def known_kb(words) -> InlineKeyboardMarkup | None:
    rows = [[known_button(w.user_word_id, w.en)] for w in words if w.is_new]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def options_kb(user_word_id: int, options: list[str]):
    kb = InlineKeyboardBuilder()
    for i, text in enumerate(options):
        kb.button(text=text, callback_data=AnswerCb(uw=user_word_id, i=i))
    kb.adjust(2)
    return kb.as_markup()


def next_question_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Дальше", callback_data="quiz_next")
    return kb.as_markup()
