"""Flaky because increment() is a non-atomic read-modify-write. The
deliberate yield point inside it makes the race manifest reliably
regardless of how fast the machine is.
"""
import threading

from src.counter import Counter


def test_three_threads_each_increment_once():
    counter = Counter()
    threads = [threading.Thread(target=counter.increment) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Bug in this test: assumes 3 concurrent increments always land as
    # exactly 3. Two threads can both read the same `current` value
    # before either writes back, so one increment is silently lost.
    assert counter.value == 3
