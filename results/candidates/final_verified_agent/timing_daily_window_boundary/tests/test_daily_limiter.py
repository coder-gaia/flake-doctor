"""Deterministic tests for DailyRateLimiter.

These tests drive the limiter through an explicit, injected clock so the
behaviour under test is fully controlled -- no reliance on the real calendar
and no randomness (previously the "same day" test rolled the simulated day
over at a random point, which made it fail whenever pytest-randomly's seed
happened to trigger the rollover).
"""
from datetime import date, timedelta

from src.daily_limiter import DailyRateLimiter


def test_fourth_call_same_day_is_rejected():
    day0 = date(2026, 1, 1)
    # All four calls land on the same calendar day.
    ticks = iter([day0] * 4)

    limiter = DailyRateLimiter(max_calls=3, today=lambda: next(ticks))
    results = [limiter.allow() for _ in range(4)]

    # The daily quota of 3 is spent by the first three calls, so the fourth
    # call on the same day must be rejected.
    assert results == [True, True, True, False]


def test_counter_resets_when_day_rolls_over():
    day0 = date(2026, 1, 1)
    day1 = day0 + timedelta(days=1)
    # Two calls on day0, then the day rolls over before the next two calls.
    ticks = iter([day0, day0, day1, day1])

    limiter = DailyRateLimiter(max_calls=3, today=lambda: next(ticks))
    results = [limiter.allow() for _ in range(4)]

    # After the rollover the counter resets, so both day1 calls are allowed.
    assert results == [True, True, True, True]


def test_quota_enforced_again_on_the_new_day():
    day0 = date(2026, 1, 1)
    day1 = day0 + timedelta(days=1)
    # One call on day0, then four calls on day1.
    ticks = iter([day0] + [day1] * 4)

    limiter = DailyRateLimiter(max_calls=3, today=lambda: next(ticks))
    results = [limiter.allow() for _ in range(5)]

    # day0: allowed. day1: 3 allowed then the 4th rejected.
    assert results == [True, True, True, True, False]
