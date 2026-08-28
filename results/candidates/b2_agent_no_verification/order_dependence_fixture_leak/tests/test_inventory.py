"""Each test gets its own fresh catalog list.

The fixture is function-scoped (the default), so a test that mutates the
list cannot leak state into whichever test runs after it -- regardless of
the order tests happen to execute in.
"""
import pytest

from src.inventory import add_item


@pytest.fixture
def catalog():
    # Function-scoped: a brand-new list object per test.
    return []


def test_add_item_appends_new_name(catalog):
    add_item(catalog, "widget")
    assert catalog == ["widget"]


def test_catalog_starts_empty_for_a_fresh_scenario(catalog):
    # Bug in this test: assumes `catalog` starts empty, which is only true
    # if it happens to run before test_add_item_appends_new_name.
    assert catalog == []
