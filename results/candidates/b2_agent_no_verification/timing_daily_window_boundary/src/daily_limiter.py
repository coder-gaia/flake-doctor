"""A naive per-day rate limiter: N calls allowed, reset when the day changes."""
from datetime import date


class DailyRateLimiter:
    """Allows up to `max_calls` per calendar day, tracked by `today()`."""

    def __init__(self, max_calls: int = 3, today=date.today):
        self._max_calls = max_calls
        self._today = today
        self._day = None
        self._count = 0

    def allow(self) -> bool:
        current_day = self._today()
        if current_day != self._day:
            self._day = current_day
            self._count = 0
        if self._count >= self._max_calls:
            return False
        self._count += 1
        return True
