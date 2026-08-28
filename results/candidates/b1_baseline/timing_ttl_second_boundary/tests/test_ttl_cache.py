"""Tests for :class:`TTLCache`.

Why this file was rewritten
---------------------------
The previous version of ``test_set_then_get_within_ttl`` seeded a fake clock
from ``pytest-randomly``'s per-test random state:

    start = 1_000.0 + random.uniform(0.80, 1.20)
    ticks = iter([start, start + 0.05])

Because ``start`` was random, the simulated wall-clock sometimes landed within
a few milliseconds of a whole-second boundary.  When that happened the
``set`` call and the ``get`` call fell on opposite sides of the boundary and
the cache appeared to "forget" a value it had been given only 50 ms earlier.
The pass/fail outcome therefore depended purely on the random seed, which is
the definition of a flaky test -- the code under test never changed between
runs.

The fix is to stop feeding randomness into the clock.  These tests now drive
``TTLCache`` with an explicit, fully controlled clock whose value only moves
when the test advances it, so every run exercises exactly the same timeline
and the assertions are deterministic.
"""

from src.ttl_cache import TTLCache


class FakeClock:
    """A deterministic, hand-cranked stand-in for ``time.monotonic``.

    Time never moves on its own: it only changes when ``advance`` is called.
    This makes the tests independent of how many times ``TTLCache`` happens
    to read the clock internally.
    """

    def __init__(self, now: float = 0.0) -> None:
        self.now = float(now)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_set_then_get_within_ttl():
    # A start time deliberately far from any one-second boundary, advanced by
    # a small, fixed amount that is comfortably inside the 1 second TTL.
    clock = FakeClock(1_000.5)
    cache = TTLCache(ttl_seconds=1, clock=clock)

    cache.set("session", "alice")
    clock.advance(0.05)

    assert cache.get("session") == "alice"


def test_get_after_ttl_expires_returns_none():
    clock = FakeClock(1_000.5)
    cache = TTLCache(ttl_seconds=1, clock=clock)

    cache.set("session", "alice")
    clock.advance(2.0)  # well past the 1 second TTL

    assert cache.get("session") is None


def test_get_missing_key_returns_none():
    clock = FakeClock(1_000.5)
    cache = TTLCache(ttl_seconds=1, clock=clock)

    assert cache.get("never-set") is None


def test_set_refreshes_ttl_window():
    clock = FakeClock(1_000.5)
    cache = TTLCache(ttl_seconds=1, clock=clock)

    cache.set("session", "alice")
    clock.advance(0.9)
    cache.set("session", "bob")  # refresh the entry near the end of the window
    clock.advance(0.5)           # 1.4s after the first set, 0.5s after the second

    assert cache.get("session") == "bob"
