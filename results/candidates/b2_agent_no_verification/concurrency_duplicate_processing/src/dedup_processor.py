"""Deduplicated processing across worker threads, e.g. for at-least-once
delivery: the same item id might arrive more than once and must only be
processed one time.
"""
import random
import threading
import time


class DedupProcessor:
    def __init__(self):
        self.seen = set()
        self.processed = []
        # Serializes the check-then-act below so it becomes a single
        # atomic operation. "Is this item already seen?" and "record it
        # as seen / processed" must not be interleaved between threads.
        self._lock = threading.Lock()

    def process(self, item):
        # Randomized scheduler yield *outside* the critical section: this
        # still lets concurrent calls fan out and genuinely overlap, so
        # the dedup logic is exercised under contention.
        time.sleep(random.uniform(0.0, 0.02))

        # The membership check and the mutation are a non-atomic
        # check-then-act. Without holding the lock across both, two
        # threads can each see `item not in self.seen` before either one
        # adds it, and the same item gets processed more than once.
        with self._lock:
            if item not in self.seen:
                time.sleep(random.uniform(0.0, 0.002))
                self.seen.add(item)
                self.processed.append(item)
