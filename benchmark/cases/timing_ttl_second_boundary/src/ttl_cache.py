"""A tiny TTL cache that buckets entries by the truncated wall-clock second.

This is a real pattern in small production systems that want O(1) expiry
without a background sweep: round the current time down to a bucket and
throw the whole bucket away once a newer bucket is observed.
"""
import time


class TTLCache:
    """Cache entries that expire after `ttl_seconds`, bucketed by second."""

    def __init__(self, ttl_seconds: int = 1, clock=time.time):
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._bucket = None
        self._store = {}

    def _current_bucket(self) -> int:
        return int(self._clock()) // self._ttl_seconds

    def set(self, key, value) -> None:
        bucket = self._current_bucket()
        if bucket != self._bucket:
            self._store = {}
            self._bucket = bucket
        self._store[key] = value

    def get(self, key, default=None):
        if self._current_bucket() != self._bucket:
            return default
        return self._store.get(key, default)
