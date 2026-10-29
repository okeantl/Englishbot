import asyncio
import sys

from bot import llm
from bot.config import settings


async def main() -> None:
    if not llm.enabled():
        sys.exit("LLM_API_KEY не задан в .env")
    print(f"API: {settings.llm_base_url}\nМодель: {settings.llm_model}\n")
    info = await llm.word_info("thoroughly")
    print(info or "Модель ответила, но не в формате JSON")


if __name__ == "__main__":
    asyncio.run(main())
