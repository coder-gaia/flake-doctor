"""A shared counter incremented from multiple threads.

The increment is a read-modify-write, which is *not* atomic in general.
To make concurrent increments safe, the read-modify-write is guarded by
a lock so that only one thread at a time can be inside the critical
section. Without the lock, two threads can read the same ``value`` before
either writes back, silently losing an increment.
"""
import random
import threading
import time


class Counter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self):
        # The randomized sleeps below only widen the window in which a
        # race could occur; they are kept so the concurrency is still
        # genuinely exercised. Correctness comes from holding the lock
        # across the entire read-modify-write.
        time.sleep(random.uniform(0.0, 0.02))
        with self._lock:
            current = self.value
            time.sleep(random.uniform(0.0, 0.002))
            self.value = current + 1
