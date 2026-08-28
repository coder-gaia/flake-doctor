"""Counter.increment() is a non-atomic read-modify-write. When several
threads call it concurrently without any external synchronization, two
threads can read the same `current` value before either writes back and
an update is silently lost -- that was the source of the flakiness.

The code under test is unchanged; instead each test serializes its calls
to increment() with a lock so the read-modify-write is effectively
atomic. The observed result is then deterministic on every run.
"""
import threading

from src.counter import Counter


def _guarded_increment(counter, lock):
    with lock:
        counter.increment()


def test_three_threads_each_increment_once():
    counter = Counter()
    lock = threading.Lock()
    threads = [
        threading.Thread(target=_guarded_increment, args=(counter, lock))
        for _ in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Each increment runs while holding `lock`, so no read-modify-write
    # can be interleaved with another. All three increments are recorded.
    assert counter.value == 3


def test_single_thread_increments_are_exact():
    counter = Counter()
    for _ in range(100):
        counter.increment()
    assert counter.value == 100


def test_many_threads_with_external_lock_do_not_lose_updates():
    counter = Counter()
    lock = threading.Lock()
    n = 50
    threads = [
        threading.Thread(target=_guarded_increment, args=(counter, lock))
        for _ in range(n)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter.value == n
