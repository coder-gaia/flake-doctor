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

    # Bug in this test: asserts one specific ordering of a `set`-backed
    # result. Set order for strings is hash-seed dependent, not
    # insertion-order, so this only holds for some process hash seeds.
    assert result == ["urgent", "billing", "retry"]
