"""Flaky because the module-scoped fixture below hands out the SAME list
to every test in this file -- a test that mutates it leaks state into
whichever test runs after it.
"""
import pytest

from src.inventory import add_item


@pytest.fixture(scope="module")
def catalog():
    # Bug: module-scoped, so this same list object is reused by every test
    # in the file instead of starting fresh for each one.
    return []


def test_add_item_appends_new_name(catalog):
    add_item(catalog, "widget")
    assert catalog == ["widget"]


def test_catalog_starts_empty_for_a_fresh_scenario(catalog):
    # Bug in this test: assumes `catalog` starts empty, which is only true
    # if it happens to run before test_add_item_appends_new_name.
    assert catalog == []
