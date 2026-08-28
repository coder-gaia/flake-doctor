"""Fetch-with-retry against a (possibly flaky) client."""
from src.http_client import TimeoutError


def fetch_with_retry(client, url, retries=3):
    last_error = None
    # MUTANT: off-by-one -- only tries `retries - 1` times, silently
    # shrinking the retry budget the caller asked for.
    for _attempt in range(retries - 1):
        try:
            return client.get(url)
        except TimeoutError as e:
            last_error = e
    raise last_error
