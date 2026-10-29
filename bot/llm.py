import json
import logging
import random
import re

from openai import AsyncOpenAI

from bot.config import settings

log = logging.getLogger(__name__)

_client = (
    AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    if settings.llm_api_key else None
)

TOPICS = [
    "путешествия", "работа в офисе", "спорт", "кулинария", "технологии", "животные", "кино",
    "здоровье", "город", "природа", "покупки", "друзья", "учёба", "музыка", "погода", "история",
    "космос", "семья", "праздники", "транспорт",
]

TEXT_PROMPT = (
    "Напиши интересный текст на английском на 120-160 слов уровня B1 на тему «{topic}». "
    "Дай заголовок в формате <b>Заголовок</b> и сам текст. Без перевода и пояснений."
)

WORD_PROMPT = (
    "Для английского слова или фразы «{word}» верни только JSON без пояснений с ключами: "
    "ipa (транскрипция IPA в британском варианте, в слешах), "
    "ru_sound (как примерно звучит русскими буквами), "
    "translation (основные переводы на русский через запятую), "
    "example (короткий пример предложения на английском)."
)


def enabled() -> bool:
    return _client is not None


async def _ask(prompt: str) -> str:
    error: Exception | None = None
    for model in [settings.llm_model, *settings.llm_fallback_models]:
        try:
            resp = await _client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.8,
            )
            content = (resp.choices[0].message.content or "").strip()
            if content:
                return content
        except Exception as e:
            log.warning("model %s failed: %s", model, e)
            error = e
    raise RuntimeError("all LLM models failed") from error


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0)) if match else {}


async def reading_text() -> str:
    return await _ask(TEXT_PROMPT.format(topic=random.choice(TOPICS)))


async def word_info(word: str) -> dict:
    return _parse_json(await _ask(WORD_PROMPT.format(word=word)))
