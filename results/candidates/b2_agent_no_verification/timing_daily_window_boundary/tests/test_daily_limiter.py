"""Behavioural tests for DailyRateLimiter.

The limiter's ``today`` hook is injected so these tests fully control the
notion of "now" -- no real calendar-day boundary is ever exercised, which
is what previously made ``test_fourth_call_same_day_is_rejected`` flaky.
"""
from datetime import date, timedelta

from src.daily_limiter import DailyRateLimiter


def test_fourth_call_same_day_is_rejected():
    day0 = date(2026, 1, 1)
    # Every call in this scenario observes the exact same calendar day, so
    # the quota of 3 is spent by the third call and the fourth is rejected.
    limiter = DailyRateLimiter(max_calls=3, today=lambda: day0)

    results = [limiter.allow() for _ in range(4)]

    assert results == [True, True, True, False]


def test_counter_resets_when_the_day_rolls_over():
    day0 = date(2026, 1, 1)
    days = [day0, day0, day0, day0 + timedelta(days=1)]
    ticks = iter(days)

    limiter = DailyRateLimiter(max_calls=3, today=lambda: next(ticks))

    results = [limiter.allow() for _ in range(4)]

    # First three exhaust day0's quota; the fourth call lands on a new day,
    # so the limiter resets and grants it.
    assert results == [True, True, True, True]
