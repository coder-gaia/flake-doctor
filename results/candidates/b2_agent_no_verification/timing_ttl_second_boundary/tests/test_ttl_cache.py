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

    # A value read 50ms after it was written is well within the 1s TTL and
    # must still be present, no matter where `start` falls relative to a
    # whole clock second.
    assert cache.get("session") == "alice"


def test_get_within_ttl_across_a_clock_second_boundary():
    # Write happens 30ms before a whole second, read happens 20ms after it.
    # Only 50ms elapse, so with a 1s TTL the value must survive.
    ticks = iter([999.97, 1000.02])

    def fake_clock():
        return next(ticks)

    cache = TTLCache(ttl_seconds=1, clock=fake_clock)
    cache.set("session", "alice")

    assert cache.get("session") == "alice"


def test_get_after_ttl_has_elapsed_returns_default():
    ticks = iter([1000.0, 1001.5])

    def fake_clock():
        return next(ticks)

    cache = TTLCache(ttl_seconds=1, clock=fake_clock)
    cache.set("session", "alice")

    assert cache.get("session", "missing") == "missing"
