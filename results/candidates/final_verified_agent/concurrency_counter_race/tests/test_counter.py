"""Counter.increment() is a read-modify-write that is only safe because it
holds a lock for the whole operation. These tests exercise that: N
concurrent increments must land as exactly N, with no lost updates.
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

    assert counter.value == 3


def test_many_threads_each_increment_once():
    counter = Counter()
    threads = [threading.Thread(target=counter.increment) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter.value == 50
