"""Flaky because add_tag's default `tags=[]` list is a single object
created once at import time and shared by every call site that relies on
the default -- including every test in this file.
"""
from src.tags import add_tag


def test_add_tag_to_a_fresh_item():
    result = add_tag("urgent")
    assert result == ["urgent"]


def test_add_tag_starts_from_an_empty_list():
    # Bug in this test: assumes the default `tags=[]` starts empty on
    # every call. It's the same list object every time the parameter
    # isn't passed explicitly, so whatever an earlier test added is
    # still there.
    result = add_tag("billing")
    assert result == ["billing"]
