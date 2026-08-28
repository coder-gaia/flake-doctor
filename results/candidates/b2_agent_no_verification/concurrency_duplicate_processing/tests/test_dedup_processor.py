"""Flaky because the dedup check-then-act in DedupProcessor.process is not
atomic: two threads can both see the item as unseen before either one
records it.
"""
import threading

from src.dedup_processor import DedupProcessor


def test_duplicate_deliveries_are_processed_once():
    processor = DedupProcessor()
    threads = [
        threading.Thread(target=processor.process, args=("order-42",))
        for _ in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Bug in this test: assumes the dedup check-then-act is atomic, so
    # three "duplicate delivery" calls for the same item always result in
    # exactly one processed entry. Two threads racing can both pass the
    # membership check before either updates `seen`, so the item gets
    # processed twice.
    assert processor.processed == ["order-42"]
