"""A tiny TTL cache that expires each entry `ttl_seconds` after it is written.

Expiry is per entry and lazy: every value is stored alongside the absolute
clock time at which it becomes stale, and a key is evicted the first time it
is read at or after that deadline. This keeps `set`/`get` O(1) without a
background sweep, while guaranteeing that a value really does live for a full
`ttl_seconds` regardless of where the write falls relative to a clock second.
"""
import time


class TTLCache:
    """Cache entries that expire `ttl_seconds` after they are written."""

    def __init__(self, ttl_seconds: int = 1, clock=time.time):
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._store = {}

    def set(self, key, value) -> None:
        self._store[key] = (value, self._clock() + self._ttl_seconds)

    def get(self, key, default=None):
        entry = self._store.get(key)
        if entry is None:
            return default
        value, expires_at = entry
        if self._clock() >= expires_at:
            del self._store[key]
            return default
        return value
