import logging
from dataclasses import dataclass

import aiohttp

from bot import llm

log = logging.getLogger(__name__)
DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"


@dataclass
class Pronunciation:
    word: str
    ipa: str | None = None
    audio_url: str | None = None
    ru_sound: str | None = None
    translation: str | None = None
    example: str | None = None


async def _from_dictionary(word: str) -> tuple[str | None, str | None]:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as http:
            async with http.get(DICT_URL.format(word=word)) as resp:
                if resp.status != 200:
                    return None, None
                data = await resp.json()
    except Exception:
        log.warning("dictionary lookup failed for %r", word)
        return None, None

    ipa = audio = None
    for entry in data:
        for ph in entry.get("phonetics", []):
            ipa = ipa or ph.get("text")
            audio = audio or ph.get("audio") or None
        ipa = ipa or entry.get("phonetic")
    return ipa, audio


async def lookup(word: str) -> Pronunciation:
    word = word.strip().lower()
    result = Pronunciation(word)
    if " " not in word:
        result.ipa, result.audio_url = await _from_dictionary(word)
    if llm.enabled():
        try:
            info = await llm.word_info(word)
            result.ipa = result.ipa or info.get("ipa")
            result.ru_sound = info.get("ru_sound")
            result.translation = info.get("translation")
            result.example = info.get("example")
        except Exception:
            log.exception("LLM word info failed for %r", word)
    return result


def format_card(p: Pronunciation, fallback_translation: str | None = None) -> str:
    lines = [f"🔊 <b>{p.word}</b>"]
    if p.ipa:
        lines.append(f"Транскрипция: {p.ipa}")
    if p.ru_sound:
        lines.append(f"Звучит как: {p.ru_sound}")
    translation = p.translation or fallback_translation
    if translation:
        lines.append(f"Перевод: {translation}")
    if p.example:
        lines.append(f"Пример: <i>{p.example}</i>")
    if len(lines) == 1:
        lines.append("Не нашёл это слово 🤷")
    return "\n".join(lines)
