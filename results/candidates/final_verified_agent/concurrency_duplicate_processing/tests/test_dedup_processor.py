"""DedupProcessor.process must treat its membership check and the follow-up
mutation as a single atomic step, otherwise concurrent duplicate deliveries
of the same item can each pass the check and be processed more than once.
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

    # Three concurrent "duplicate delivery" calls for the same item must
    # still result in exactly one processed entry.
    assert processor.processed == ["order-42"]


def test_many_concurrent_duplicates_across_several_items():
    processor = DedupProcessor()
    items = [f"order-{i}" for i in range(5)]
    threads = [
        threading.Thread(target=processor.process, args=(item,))
        for item in items
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(processor.processed) == sorted(items)
    assert processor.seen == set(items)
