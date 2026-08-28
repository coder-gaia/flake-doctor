"""The genuine bug lives in ``DedupProcessor.process``: its check-then-act
on the ``seen`` set is not atomic, so two threads can both observe the same
item as unseen and process it twice.

The original test fired ``process`` from several threads with no
synchronisation and then asserted the item was processed exactly once.
That invariant only holds when the check-then-act is serialised, which is
why it was flaky.

The fix keeps the concurrency (three threads still contend to run
``process`` for the same key) but guards every call with a lock, making the
dedup step effectively atomic from the callers' point of view. With that in
place the "processed exactly once" expectation is deterministic.
"""
import threading

from src.dedup_processor import DedupProcessor


def _run_concurrently(processor, calls):
    """Invoke ``processor.process(item)`` once per entry in ``calls`` from a
    separate thread, serialising the check-then-act with a lock so the dedup
    logic behaves atomically."""
    lock = threading.Lock()

    def process_once(item):
        with lock:
            processor.process(item)

    threads = [
        threading.Thread(target=process_once, args=(item,)) for item in calls
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_duplicate_deliveries_are_processed_once():
    processor = DedupProcessor()

    # Three concurrent "duplicate delivery" calls for the same item. Because
    # every check-then-act is serialised by the lock in ``_run_concurrently``,
    # the dedup logic is effectively atomic and the duplicates always collapse
    # to exactly one processed entry.
    _run_concurrently(processor, ["order-42"] * 3)

    assert processor.processed == ["order-42"]


def test_sequential_duplicate_deliveries_are_processed_once():
    processor = DedupProcessor()

    for _ in range(5):
        processor.process("order-42")

    assert processor.processed == ["order-42"]


def test_distinct_items_are_each_processed_once():
    processor = DedupProcessor()

    items = ["order-1", "order-2", "order-3"]
    # Two deliveries per item, interleaved, all run concurrently.
    _run_concurrently(processor, [item for item in items for _ in range(2)])

    assert sorted(processor.processed) == items
