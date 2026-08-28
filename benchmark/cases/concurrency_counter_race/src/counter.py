"""A shared counter incremented from multiple threads via a non-atomic
read-modify-write.
"""
import random
import time


class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        # Two deliberate, randomized scheduler yields. All threads start
        # within microseconds of each other, so without a wide stagger
        # *before* the read, every thread's read would happen before any
        # thread's write regardless of what follows -- guaranteeing a
        # collision every single time instead of sometimes. The wide
        # stagger spreads threads out enough that they usually don't
        # overlap; the narrow window between read and write is the actual
        # vulnerability that occasionally lets two staggered threads still
        # collide. A real (if tiny) sleep releases the GIL long enough for
        # another thread to actually run -- time.sleep(0) is only a
        # scheduling *hint* and isn't reliable enough to force a context
        # switch.
        time.sleep(random.uniform(0.0, 0.02))  # wide stagger
        current = self.value
        time.sleep(random.uniform(0.0, 0.002))  # narrow race window
        self.value = current + 1
