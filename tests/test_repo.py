import os
from datetime import date, timedelta

os.environ.setdefault("BOT_TOKEN", "test")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest  # noqa: E402

from bot import repo  # noqa: E402
from bot.db import Base, Session, engine  # noqa: E402

D = date(2026, 1, 1)


def day(n: int) -> date:
    return D + timedelta(days=n)


@pytest.fixture
async def session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as s:
        await repo.seed_words(s)
        yield s


async def test_same_list_on_same_day(session):
    user = await repo.get_or_create_user(session, 1)
    first = await repo.todays_words(session, user, D)
    second = await repo.todays_words(session, user, D)
    assert len(first) == 10 and all(w.is_new for w in first)
    assert [w.user_word_id for w in first] == [w.user_word_id for w in second]


async def test_next_day_keeps_old_words_and_adds_five(session):
    user = await repo.get_or_create_user(session, 1)
    first = await repo.todays_words(session, user, day(0))
    second = await repo.todays_words(session, user, day(1))
    assert len(second) == 15
    assert [w.en for w in second[:10]] == [w.en for w in first]
    assert not any(w.is_new for w in second[:10])
    assert all(w.is_new for w in second[10:])


async def test_new_cycle_has_only_unseen_words(session):
    user = await repo.get_or_create_user(session, 1)
    cycle1 = [await repo.todays_words(session, user, day(i)) for i in range(5)]
    assert [len(c) for c in cycle1] == [10, 15, 20, 25, 30]

    cycle2 = await repo.todays_words(session, user, day(5))
    assert user.cycle == 2 and len(cycle2) == 10
    assert not {w.en for w in cycle2} & {w.en for w in cycle1[-1]}


async def test_known_word_is_replaced(session):
    user = await repo.get_or_create_user(session, 1)
    words = await repo.todays_words(session, user, D)
    replacement = await repo.mark_known(session, user, words[0].user_word_id, D)
    assert replacement is not None and replacement.en not in {w.en for w in words}

    now = await repo.todays_words(session, user, D)
    assert len(now) == 10
    assert words[0].en not in {w.en for w in now}
    assert await repo.mark_known(session, user, words[0].user_word_id, D) is None


async def test_quiz_uses_current_cycle(session):
    user = await repo.get_or_create_user(session, 1)
    words = await repo.todays_words(session, user, D)
    q = await repo.next_question(session, user)
    assert q.en in {w.en for w in words} and q.answer in q.options and len(q.options) == 4

    correct, word = await repo.answer(session, 1, q.user_word_id, q.answer)
    assert correct and word.en == q.en
    assert await repo.answer(session, 2, q.user_word_id, q.answer) is None


async def test_add_words_skips_duplicates(session):
    added = await repo.add_words(session, [{"en": "Zxqword ", "ru": "тест"}, {"en": "zxqword", "ru": "тест"},
                                           {"en": "time", "ru": "время"}])
    assert added == 1
