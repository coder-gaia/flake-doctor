"""These tests each rely on ``add_tag`` starting from a fresh, empty list
when ``tags`` isn't passed explicitly. That only holds if ``add_tag``
builds a new list per call instead of reusing a mutable default argument
(the previous ``tags=[]`` shared one list across every call, which made
these tests order-dependent and flaky under pytest-randomly).
"""
from src.tags import add_tag


def test_add_tag_to_a_fresh_item():
    result = add_tag("urgent")
    assert result == ["urgent"]


def test_add_tag_starts_from_an_empty_list():
    result = add_tag("billing")
    assert result == ["billing"]


def test_add_tag_appends_to_a_supplied_list():
    result = add_tag("second", ["first"])
    assert result == ["first", "second"]


def test_add_tag_does_not_duplicate_existing_item():
    result = add_tag("dup", ["dup"])
    assert result == ["dup"]
