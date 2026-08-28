"""Order-preserving dedupe.

``dedupe_tags`` must return elements in first-seen order with later
duplicates removed. The previous implementation used ``list(set(tags))``,
whose ordering depends on the per-process string hash seed, so this test
passed or failed depending on ``PYTHONHASHSEED``. That flakiness only
surfaces across fresh Python processes (as a CI flake detector reruns a
suspected flake), never when rerun inside one process.
"""
from src.dedupe import dedupe_tags


def test_dedupe_preserves_a_specific_order():
    tags = ["urgent", "billing", "urgent", "retry"]

    result = dedupe_tags(tags)

    # First-seen order, later duplicates dropped. Deterministic regardless
    # of the process hash seed now that dedupe_tags no longer goes via set.
    assert result == ["urgent", "billing", "retry"]


def test_dedupe_preserves_order_with_trailing_duplicate():
    tags = ["retry", "billing", "urgent", "billing", "retry"]

    result = dedupe_tags(tags)

    assert result == ["retry", "billing", "urgent"]


def test_dedupe_no_duplicates_is_identity():
    tags = ["a", "b", "c", "d"]

    assert dedupe_tags(tags) == ["a", "b", "c", "d"]


def test_dedupe_empty():
    assert dedupe_tags([]) == []
