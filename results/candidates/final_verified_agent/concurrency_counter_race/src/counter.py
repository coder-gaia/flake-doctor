"""A shared counter that can be safely incremented from multiple threads.

The increment is a read-modify-write, which is not atomic in CPython once
the GIL can be released between the read and the write (e.g. across a
blocking call). A lock makes the whole read-modify-write atomic so
concurrent increments can't lose an update.
"""
import random
import threading
import time


class Counter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self):
        # The sleeps below widen the window in which a context switch can
        # happen; they are kept so the race is easy to provoke, but the
        # lock guarantees the read-modify-write is still atomic.
        time.sleep(random.uniform(0.0, 0.02))
        with self._lock:
            current = self.value
            time.sleep(random.uniform(0.0, 0.002))
            self.value = current + 1
