"""Flaky because it exercises a real wall-clock second boundary.

The fake clock below is seeded from pytest-randomly's per-test random state,
so the benchmark's flake rate is controllable and reproducible across
machines, while `TTLCache` itself still runs against a normal-looking clock
function -- the bug under test is real, only the clock driving it is
simulated to keep this deterministic in CI.
"""
import random

from src.ttl_cache import TTLCache


def test_set_then_get_within_ttl():
    # Simulate a wall-clock that sits close to a second boundary a fraction
    # of the time. pytest-randomly reseeds `random` per test, so this
    # position differs (reproducibly) run to run.
    start = 1_000.0 + random.uniform(0.80, 1.20)
    ticks = iter([start, start + 0.05])

    def fake_clock():
        return next(ticks)

    cache = TTLCache(ttl_seconds=1, clock=fake_clock)
    cache.set("session", "alice")

    # A read 50ms after the write is well within the 1s TTL, so the value
    # must still be there no matter where `start` falls relative to a
    # wall-clock second boundary. (The old cache bucketed by truncated
    # second and forgot entries written just before a boundary.)
    assert cache.get("session") == "alice"


def test_get_just_before_boundary_then_just_after():
    # `set` lands 30ms before a whole second, `get` lands 40ms after it:
    # 70ms elapsed, far short of the 1s TTL. Deterministic regression test
    # for the second-boundary bug (no randomness involved).
    ticks = iter([1_000.97, 1_001.01])

    def fake_clock():
        return next(ticks)

    cache = TTLCache(ttl_seconds=1, clock=fake_clock)
    cache.set("session", "alice")
    assert cache.get("session") == "alice"


def test_entry_expires_after_ttl_elapses():
    ticks = iter([100.0, 101.5])

    def fake_clock():
        return next(ticks)

    cache = TTLCache(ttl_seconds=1, clock=fake_clock)
    cache.set("session", "alice")
    assert cache.get("session", "gone") == "gone"
