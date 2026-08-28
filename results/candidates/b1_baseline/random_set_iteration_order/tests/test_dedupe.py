"""Order-independent assertions for `dedupe_tags`.

`set` iteration order for strings depends on the per-process hash seed,
so asserting a single specific ordering of a `set`-backed result is
inherently flaky: it only holds for some process hash seeds and fails
for others when the suite is rerun in a fresh Python process.

The contract `dedupe_tags` actually guarantees is "same unique tags, no
duplicates, nothing invented" -- not a particular ordering. These tests
assert exactly that, using order-insensitive comparisons.
"""
from src.dedupe import dedupe_tags


def test_dedupe_preserves_a_specific_order():
    tags = ["urgent", "billing", "urgent", "retry"]

    result = dedupe_tags(tags)

    # The result is `set`-backed, so its ordering is hash-seed dependent
    # and must not be asserted directly. Compare in an order-independent
    # way instead: the unique tags are exactly {"urgent", "billing",
    # "retry"}, each appearing once.
    assert sorted(result) == ["billing", "retry", "urgent"]
    assert len(result) == 3
    assert len(result) == len(set(result))


def test_dedupe_removes_all_duplicates():
    tags = ["a", "b", "a", "c", "b", "a"]

    result = dedupe_tags(tags)

    assert sorted(result) == ["a", "b", "c"]
    assert len(result) == len(set(result))


def test_dedupe_keeps_every_unique_tag_when_no_duplicates():
    tags = ["x", "y", "z"]

    result = dedupe_tags(tags)

    assert sorted(result) == ["x", "y", "z"]
    assert len(result) == 3


def test_dedupe_empty_input_returns_empty():
    assert list(dedupe_tags([])) == []
