import json
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import logic
from bot.db import User, UserWord, Word

WORDS_FILE = Path(__file__).resolve().parent.parent / "data" / "words.json"


async def add_words(session: AsyncSession, items: list[dict]) -> int:
    existing = set(await session.scalars(select(Word.en)))
    new, seen = [], set()
    for i in items:
        en = i["en"].strip().lower()
        if en and en not in existing and en not in seen:
            seen.add(en)
            new.append(Word(en=en, ru=i["ru"].strip()))
    session.add_all(new)
    await session.commit()
    return len(new)


async def seed_words(session: AsyncSession) -> int:
    return await add_words(session, json.loads(WORDS_FILE.read_text(encoding="utf-8")))


async def get_or_create_user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, cycle=1, streak=0)
        session.add(user)
        await session.commit()
    return user


async def touch(session: AsyncSession, user: User, today: date) -> None:
    user.streak = logic.update_streak(user.last_active, user.streak, today)
    user.last_active = today
    await session.commit()


@dataclass
class CycleWord:
    user_word_id: int
    en: str
    ru: str
    is_new: bool


async def cycle_words(session: AsyncSession, user: User, today: date) -> list[CycleWord]:
    rows = await session.execute(
        select(UserWord, Word).join(Word)
        .where(UserWord.user_id == user.id, UserWord.cycle == user.cycle, UserWord.known.is_(False))
        .order_by(UserWord.id)
    )
    return [CycleWord(uw.id, w.en, w.ru, uw.introduced_on == today) for uw, w in rows]


async def _issue_fresh(session: AsyncSession, user: User, count: int, today: date) -> list[CycleWord]:
    already = select(UserWord.word_id).where(UserWord.user_id == user.id)
    fresh = list(await session.scalars(
        select(Word).where(Word.id.not_in(already)).order_by(Word.id).limit(count)
    ))
    issued = [UserWord(user_id=user.id, word_id=w.id, cycle=user.cycle, introduced_on=today) for w in fresh]
    session.add_all(issued)
    await session.flush()
    return [CycleWord(uw.id, w.en, w.ru, True) for uw, w in zip(issued, fresh)]


async def todays_words(session: AsyncSession, user: User, today: date) -> list[CycleWord]:
    if user.last_issue != today:
        size = len(await cycle_words(session, user, today))
        new_cycle, count = logic.plan_day(size)
        if new_cycle:
            user.cycle += 1
        await _issue_fresh(session, user, count, today)
        user.last_issue = today
        await session.commit()
    return await cycle_words(session, user, today)


async def mark_known(session: AsyncSession, user: User, user_word_id: int,
                     today: date) -> CycleWord | None:
    uw = await session.get(UserWord, user_word_id)
    if uw is None or uw.user_id != user.id or uw.known:
        return None
    uw.known = True
    replacement = await _issue_fresh(session, user, 1, today)
    await session.commit()
    return replacement[0] if replacement else None


@dataclass
class Question:
    user_word_id: int
    en: str
    options: list[str]
    answer: str


async def next_question(session: AsyncSession, user: User) -> Question | None:
    row = (await session.execute(
        select(UserWord, Word).join(Word)
        .where(UserWord.user_id == user.id, UserWord.cycle == user.cycle, UserWord.known.is_(False))
        .order_by(func.random()).limit(1)
    )).first()
    if row is None:
        return None
    uw, word = row
    wrong = list(await session.scalars(
        select(Word.ru).where(Word.id != word.id).order_by(func.random()).limit(3)
    ))
    options = wrong + [word.ru]
    random.shuffle(options)
    return Question(uw.id, word.en, options, word.ru)


async def answer(session: AsyncSession, user_id: int, user_word_id: int,
                 chosen: str) -> tuple[bool, Word] | None:
    uw = await session.get(UserWord, user_word_id)
    if uw is None or uw.user_id != user_id:
        return None
    word = await session.get(Word, uw.word_id)
    correct = chosen == word.ru
    if correct:
        uw.correct += 1
    else:
        uw.wrong += 1
    await session.commit()
    return correct, word


async def find_word(session: AsyncSession, en: str) -> Word | None:
    return await session.scalar(select(Word).where(Word.en == en.lower()))


@dataclass
class Stats:
    total: int
    known: int
    cycle: int
    cycle_size: int
    streak: int
    left_in_dictionary: int


async def stats(session: AsyncSession, user: User, today: date) -> Stats:
    base = select(func.count()).select_from(UserWord).where(UserWord.user_id == user.id)
    total = await session.scalar(base)
    return Stats(
        total=total,
        known=await session.scalar(base.where(UserWord.known.is_(True))),
        cycle=user.cycle,
        cycle_size=len(await cycle_words(session, user, today)),
        streak=user.streak,
        left_in_dictionary=await session.scalar(select(func.count()).select_from(Word)) - total,
    )
