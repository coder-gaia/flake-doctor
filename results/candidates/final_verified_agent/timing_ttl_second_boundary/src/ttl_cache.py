"""A tiny TTL cache with lazy, per-entry expiry.

Small production systems often want O(1) expiry without a background sweep.
The trick is to stamp every entry with an absolute deadline when it is
written (`now + ttl_seconds`) and to check that deadline lazily on read,
evicting the entry if it has passed.

An earlier version bucketed entries by the truncated wall-clock second and
threw the whole bucket away once a newer bucket was observed. That made an
entry's real lifetime anything between ~0 and `ttl_seconds`: a value written
just before a second boundary was forgotten milliseconds later. Stamping each
entry with its own deadline keeps expiry O(1) while actually honouring
`ttl_seconds` regardless of where `set` falls relative to a second boundary.
"""
import time


class TTLCache:
    """Cache entries that expire `ttl_seconds` after they are written."""

    def __init__(self, ttl_seconds: int = 1, clock=time.time):
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        # key -> (value, expires_at)
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
