"""A fake HTTP client for benchmark purposes -- no real network calls are
ever made. Simulates transient timeouts at a fixed probability, the way a
flaky upstream dependency would in a real integration test.
"""
import random


class TimeoutError(Exception):
    pass


class FakeClient:
    def __init__(self, failure_rate=0.15):
        self.failure_rate = failure_rate
        self.calls = 0

    def get(self, url):
        self.calls += 1
        if random.random() < self.failure_rate:
            raise TimeoutError(f"simulated timeout for {url}")
        return {"status": 200, "url": url}
