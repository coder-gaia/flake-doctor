"""Flaky because it hardcodes an exact call count against a client whose
failures are randomized. pytest-randomly reseeds `random` before every
test, so how many attempts happen before success varies run to run.

No real network I/O happens anywhere in this case -- FakeClient simulates
timeouts with `random.random()`, which keeps the case sandboxed and
reproducible without depending on an actual flaky endpoint.
"""
from src.fetch import fetch_with_retry
from src.http_client import FakeClient


def test_fetch_succeeds_within_three_retries():
    client = FakeClient(failure_rate=0.15)
    fetch_with_retry(client, "https://example.invalid/data", retries=3)

    # Bug in this test: hardcodes "exactly 1 call" as if the number of
    # attempts before success were deterministic. With a 15% simulated
    # failure rate, most calls succeed immediately, but roughly one run
    # in seven needs at least one retry.
    assert client.calls == 1
