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

    # Bug in this test: it assumes `set` and `get` always land in the same
    # one-second bucket. When `start` sits within ~0.05s of a boundary, the
    # second call crosses into the next bucket and the cache "forgets" a
    # value it was just given 50ms ago.
    assert cache.get("session") == "alice"
