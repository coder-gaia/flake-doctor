"""Fetch-with-retry against a (possibly flaky) client."""
from src.http_client import TimeoutError


def fetch_with_retry(client, url, retries=3):
    last_error = None
    for _attempt in range(retries):
        try:
            return client.get(url)
        except TimeoutError as e:
            last_error = e
    raise last_error
