"""Flaky across fresh processes, not within one.

`set` iteration order for strings depends on the per-process hash seed.
Rerunning the same test 50 times inside one pytest process will never show
this -- the seed doesn't change mid-process. It only shows up when the
test suite is invoked as fresh Python processes, which is exactly how a
real CI matrix (and this benchmark's detector) reruns a suspected flake.
"""
from src.dedupe import dedupe_tags


def test_dedupe_preserves_a_specific_order():
    tags = ["urgent", "billing", "urgent", "retry"]

    result = dedupe_tags(tags)

    # `dedupe_tags` keeps the first occurrence of each tag and preserves
    # insertion order, so the result is deterministic across processes.
    assert result == ["urgent", "billing", "retry"]


def test_dedupe_preserves_order_for_many_tags():
    tags = ["z", "a", "m", "a", "z", "q", "m", "b"]

    assert dedupe_tags(tags) == ["z", "a", "m", "q", "b"]


def test_dedupe_no_duplicates_is_identity():
    tags = ["one", "two", "three"]

    assert dedupe_tags(tags) == ["one", "two", "three"]


def test_dedupe_empty():
    assert dedupe_tags([]) == []
