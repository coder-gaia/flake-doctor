"""These tests were flaky because add_tag used a mutable default argument
(`tags=[]`), a single list object created once at import time and shared
by every call that relied on the default. With pytest-randomly shuffling
test order, whichever test ran first left its tag behind for the next.

`add_tag` now uses a `None` sentinel and builds a fresh list per call, so
each call that omits `tags` starts from an empty list regardless of order.
"""
from src.tags import add_tag


def test_add_tag_to_a_fresh_item():
    result = add_tag("urgent")
    assert result == ["urgent"]


def test_add_tag_starts_from_an_empty_list():
    # Each call that omits `tags` must start from an empty list, no matter
    # what earlier calls did.
    result = add_tag("billing")
    assert result == ["billing"]


def test_add_tag_appends_to_a_caller_supplied_list():
    existing = ["urgent"]
    result = add_tag("billing", existing)
    assert result == ["urgent", "billing"]
    assert result is existing


def test_add_tag_does_not_duplicate_existing_tag():
    result = add_tag("urgent", ["urgent"])
    assert result == ["urgent"]
