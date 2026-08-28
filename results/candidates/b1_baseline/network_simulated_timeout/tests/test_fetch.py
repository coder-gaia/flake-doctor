"""Previously flaky: the test hardcoded an exact call count against a
client whose failures are randomized. pytest-randomly reseeds `random`
before every test, so the number of attempts before success varied from
run to run, and "exactly 1 call" held only when no retry happened to be
needed.

The fix asserts on the contract that actually matters -- that
`fetch_with_retry` succeeds without exceeding the configured retry
budget -- instead of a specific attempt count that depends on the RNG.

No real network I/O happens anywhere here: FakeClient simulates timeouts
with `random.random()`, which keeps the case sandboxed and reproducible
without depending on an actual flaky endpoint.
"""
import pytest

from src.fetch import fetch_with_retry
from src.http_client import FakeClient


def test_fetch_succeeds_within_three_retries():
    client = FakeClient(failure_rate=0.15)

    # Should not raise: with retries=3 there are up to four attempts, and
    # a 15% simulated failure rate makes total exhaustion astronomically
    # unlikely.
    fetch_with_retry(client, "https://example.invalid/data", retries=3)

    # How many attempts happen before success depends on the reseeded
    # RNG, so we only assert the retry budget was respected: at least one
    # call was made and no more than the initial attempt plus three
    # retries.
    assert 1 <= client.calls <= 4


def test_fetch_makes_single_call_when_client_never_fails():
    client = FakeClient(failure_rate=0.0)

    fetch_with_retry(client, "https://example.invalid/data", retries=3)

    # With no simulated failures the very first attempt always succeeds,
    # so this count is genuinely deterministic.
    assert client.calls == 1


def test_fetch_retries_then_raises_when_client_always_fails():
    client = FakeClient(failure_rate=1.0)

    with pytest.raises(Exception):
        fetch_with_retry(client, "https://example.invalid/data", retries=3)

    # Every attempt fails, so retrying must have occurred (more than the
    # single initial attempt) without exceeding the retry budget.
    assert 2 <= client.calls <= 4
