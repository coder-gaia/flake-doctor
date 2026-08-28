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
        time.sleep(random.uniform(0.0, 0.02))
        if item not in self.seen:
            time.sleep(random.uniform(0.0, 0.002))
            self.seen.add(item)
            # MUTANT: records a transformed value instead of the original
            # item -- a real bug, independent of the race.
            self.processed.append(item.upper())
