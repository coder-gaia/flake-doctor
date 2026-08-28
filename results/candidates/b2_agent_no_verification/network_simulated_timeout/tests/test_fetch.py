"""Tests for ``fetch_with_retry``.

Root cause of the historical flakiness
--------------------------------------
This test used to drive ``fetch_with_retry`` with ``FakeClient``, whose
timeouts are decided by ``random.random()``. ``pytest-randomly`` reseeds the
global ``random`` module before every test, so the number of simulated
timeouts before the first success changed from run to run. The test then
asserted ``client.calls == 1``, which only held on seeds where the very first
call happened not to time out -- roughly one run in seven failed instead.

The fix is to exercise the retry logic with a *deterministic* client that is
scripted to time out a fixed number of times and then succeed. That makes the
attempt count knowable and actually pins down the behaviour the test name
promises: a success that arrives within the retry budget.
"""
from src.fetch import fetch_with_retry
from src.http_client import FakeClient, TimeoutError


class ScriptedClient:
    """Times out ``fail_times`` times, then returns a normal response.

    Deterministic: no RNG involved, so the number of attempts
    ``fetch_with_retry`` makes is fully predictable.
    """

    def __init__(self, fail_times):
        self.fail_times = fail_times
        self.calls = 0

    def get(self, url):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise TimeoutError(f"simulated timeout for {url}")
        return {"status": 200, "url": url}


def test_fetch_succeeds_within_three_retries():
    # Two transient timeouts, then success -- comfortably inside a budget
    # of three attempts.
    client = ScriptedClient(fail_times=2)

    result = fetch_with_retry(client, "https://example.invalid/data", retries=3)

    assert result == {"status": 200, "url": "https://example.invalid/data"}
    # Exactly the two failed attempts plus the one that succeeded; it must
    # not keep calling once it has a good response.
    assert client.calls == 3


def test_fetch_succeeds_on_first_attempt_makes_one_call():
    client = ScriptedClient(fail_times=0)

    result = fetch_with_retry(client, "https://example.invalid/data", retries=3)

    assert result == {"status": 200, "url": "https://example.invalid/data"}
    assert client.calls == 1


def test_fetch_gives_up_after_exhausting_retries():
    client = ScriptedClient(fail_times=99)

    try:
        fetch_with_retry(client, "https://example.invalid/data", retries=3)
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected TimeoutError to propagate")

    assert client.calls == 3


def test_fake_client_never_fails_when_failure_rate_is_zero():
    # A regression guard that does not depend on the global RNG seed.
    client = FakeClient(failure_rate=0.0)

    result = fetch_with_retry(client, "https://example.invalid/data", retries=3)

    assert result["status"] == 200
    assert client.calls == 1
