"""Counter.increment() performs a read-modify-write that is only safe
because it is guarded by a lock. These tests exercise many concurrent
increments to make sure no update is lost.
"""
import threading

from src.counter import Counter


def _run_concurrent_increments(n):
    counter = Counter()
    threads = [threading.Thread(target=counter.increment) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return counter.value


def test_three_threads_each_increment_once():
    assert _run_concurrent_increments(3) == 3


def test_many_threads_each_increment_once():
    assert _run_concurrent_increments(50) == 50
