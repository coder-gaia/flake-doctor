"""A shared counter incremented from multiple threads via a non-atomic
read-modify-write.
"""
import random
import time


class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        time.sleep(random.uniform(0.0, 0.02))
        current = self.value
        time.sleep(random.uniform(0.0, 0.002))
        # MUTANT: increments by 2 instead of 1.
        self.value = current + 2
