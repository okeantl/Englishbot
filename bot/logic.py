from datetime import date, timedelta

START_WORDS = 10
STEP_WORDS = 5
CYCLE_MAX = 30


def plan_day(cycle_size: int) -> tuple[bool, int]:
    if cycle_size == 0:
        return False, START_WORDS
    if cycle_size >= CYCLE_MAX:
        return True, START_WORDS
    return False, min(STEP_WORDS, CYCLE_MAX - cycle_size)


def update_streak(last_active: date | None, streak: int, today: date) -> int:
    if last_active == today:
        return streak
    if last_active == today - timedelta(days=1):
        return streak + 1
    return 1
