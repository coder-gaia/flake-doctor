"""Deterministic tests for DailyRateLimiter.

The previous version of ``test_fourth_call_same_day_is_rejected`` was flaky
because it used ``random.choices`` to sometimes simulate the calendar day
rolling over partway through the four calls. When the day rolled over, the
limiter legitimately reset its per-day counter and granted a fourth call,
which contradicted the test's hard-coded expectation of
``[True, True, True, False]``.

The fix is to stop injecting randomness: pin the simulated "today" to a
single fixed date for the same-day test so all four calls are guaranteed to
land on the same day. The day-rollover behavior is genuinely interesting, so
it is covered explicitly by a separate, fully deterministic test.
"""
from datetime import date, timedelta

from src.daily_limiter import DailyRateLimiter


def test_fourth_call_same_day_is_rejected():
    day0 = date(2026, 1, 1)
    # All four calls deliberately observe the same calendar day, so once the
    # daily quota of 3 is spent the fourth call must be rejected.
    ticks = iter([day0] * 4)

    limiter = DailyRateLimiter(max_calls=3, today=lambda: next(ticks))
    results = [limiter.allow() for _ in range(4)]

    assert results == [True, True, True, False]


def test_counter_resets_when_day_rolls_over():
    day0 = date(2026, 1, 1)
    day1 = day0 + timedelta(days=1)
    # First three calls exhaust day0's quota; the day then rolls over before
    # the fourth call, so the limiter should reset and allow it.
    ticks = iter([day0, day0, day0, day1])

    limiter = DailyRateLimiter(max_calls=3, today=lambda: next(ticks))
    results = [limiter.allow() for _ in range(4)]

    assert results == [True, True, True, True]


def test_quota_enforced_again_after_rollover():
    day0 = date(2026, 1, 1)
    day1 = day0 + timedelta(days=1)
    # Spend day0's quota (3 allowed, 1 rejected), then roll over to day1 and
    # confirm the fresh quota is once more capped at 3.
    ticks = iter([day0, day0, day0, day0, day1, day1, day1, day1])

    limiter = DailyRateLimiter(max_calls=3, today=lambda: next(ticks))
    results = [limiter.allow() for _ in range(8)]

    assert results == [True, True, True, False, True, True, True, False]
