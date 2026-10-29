from datetime import date, timedelta

import pytest

from bot import logic

D = date(2026, 1, 1)


@pytest.mark.parametrize("size, expected", [
    (0, (False, 10)),
    (10, (False, 5)),
    (25, (False, 5)),
    (28, (False, 2)),
    (30, (True, 10)),
])
def test_plan_day(size, expected):
    assert logic.plan_day(size) == expected


def test_cycle_grows_10_15_20_25_30_then_restarts():
    size, sizes = 0, []
    for _ in range(7):
        new_cycle, count = logic.plan_day(size)
        size = count if new_cycle else size + count
        sizes.append(size)
    assert sizes == [10, 15, 20, 25, 30, 10, 15]


@pytest.mark.parametrize("last, streak, expected", [
    (None, 0, 1),
    (D, 4, 4),
    (D - timedelta(days=1), 4, 5),
    (D - timedelta(days=3), 4, 1),
])
def test_streak(last, streak, expected):
    assert logic.update_streak(last, streak, D) == expected
