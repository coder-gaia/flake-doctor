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
        # The membership check and the subsequent mutation of `seen` /
        # `processed` must happen as one atomic step. Without this lock two
        # threads can both observe `item not in self.seen` before either of
        # them records it, and the item gets processed more than once.
        self._lock = threading.Lock()

    def process(self, item):
        # Keep the randomized scheduler yield *outside* the critical section
        # so concurrent calls still interleave heavily before contending for
        # the lock -- this is what used to expose the check-then-act race.
        time.sleep(random.uniform(0.0, 0.02))
        with self._lock:
            if item not in self.seen:
                time.sleep(random.uniform(0.0, 0.002))
                self.seen.add(item)
                self.processed.append(item)
