"""Flaky because it exercises a real calendar-day boundary.

Seeded from pytest-randomly's per-test random state so the flake rate is
reproducible across machines without needing to wait for real midnight.
"""
import random
from datetime import date, timedelta

from src.daily_limiter import DailyRateLimiter


def test_fourth_call_same_day_is_rejected():
    day0 = date(2026, 1, 1)
    # Most of the time all four calls see the same date. A fraction of the
    # time, the simulated day rolls over partway through the sequence --
    # exactly like a limiter that reads date.today() right at midnight.
    roll_at = random.choices([None, 2, 3], weights=[85, 8, 7])[0]
    days = [day0] * 4
    if roll_at is not None:
        for i in range(roll_at, 4):
            days[i] = day0 + timedelta(days=1)
    ticks = iter(days)

    limiter = DailyRateLimiter(max_calls=3, today=lambda: next(ticks))
    results = [limiter.allow() for _ in range(4)]

    # Bug in this test: it assumes all four calls land on the same day, so
    # the fourth call should always be rejected once the daily quota of 3
    # is spent. When the simulated day rolls over before the fourth call,
    # the limiter resets its counter and grants a call it shouldn't have.
    assert results == [True, True, True, False]
