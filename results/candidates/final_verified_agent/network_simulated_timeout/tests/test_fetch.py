"""Tests for `fetch_with_retry`.

The previous version of `test_fetch_succeeds_within_three_retries` was flaky:
it drove failures through `FakeClient`, whose timeouts come from the global
`random` module, and then asserted an exact call count (`client.calls == 1`).
pytest-randomly reseeds `random` before every test, so the number of attempts
before a success varied from run to run and the assertion failed roughly one
run in seven.

The retry contract doesn't actually depend on randomness, so these tests pin
the client's behaviour explicitly: fail a fixed number of times, then succeed.
"""
from src.fetch import fetch_with_retry
from src.http_client import TimeoutError


class ProgrammableClient:
    """A client that raises TimeoutError for the first `fail_times` calls,
    then returns a normal response. Fully deterministic."""

    def __init__(self, fail_times):
        self.fail_times = fail_times
        self.calls = 0

    def get(self, url):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise TimeoutError(f"simulated timeout for {url}")
        return {"status": 200, "url": url}


def test_fetch_succeeds_within_three_retries():
    # Two transient timeouts, then success -- the third attempt (still within
    # retries=3) must succeed.
    client = ProgrammableClient(fail_times=2)

    result = fetch_with_retry(client, "https://example.invalid/data", retries=3)

    assert result == {"status": 200, "url": "https://example.invalid/data"}
    assert client.calls == 3


def test_fetch_succeeds_immediately_when_client_healthy():
    client = ProgrammableClient(fail_times=0)

    result = fetch_with_retry(client, "https://example.invalid/data", retries=3)

    assert result == {"status": 200, "url": "https://example.invalid/data"}
    assert client.calls == 1


def test_fetch_raises_after_exhausting_retries():
    # Every attempt times out -- fetch_with_retry should give up after exactly
    # `retries` attempts and re-raise the last TimeoutError.
    client = ProgrammableClient(fail_times=99)

    try:
        fetch_with_retry(client, "https://example.invalid/data", retries=3)
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected TimeoutError to be raised")

    assert client.calls == 3
