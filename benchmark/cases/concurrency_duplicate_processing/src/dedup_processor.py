"""Deduplicated processing across worker threads, e.g. for at-least-once
delivery: the same item id might arrive more than once and must only be
processed one time.
"""
import random
import time


class DedupProcessor:
    def __init__(self):
        self.seen = set()
        self.processed = []

    def process(self, item):
        # Two deliberate, randomized scheduler yields -- same technique as
        # concurrency_counter_race. The wide stagger spreads concurrent
        # calls out enough that they usually don't collide; the narrow
        # window between the membership check and the mutation is the
        # actual vulnerability: it's a non-atomic check-then-act, so two
        # threads can both see `item not in self.seen` before either one
        # adds it.
        time.sleep(random.uniform(0.0, 0.02))
        if item not in self.seen:
            time.sleep(random.uniform(0.0, 0.002))
            self.seen.add(item)
            self.processed.append(item)
