from datetime import date, datetime
from zoneinfo import ZoneInfo

from bot.config import settings

TZ = ZoneInfo(settings.timezone)


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()
