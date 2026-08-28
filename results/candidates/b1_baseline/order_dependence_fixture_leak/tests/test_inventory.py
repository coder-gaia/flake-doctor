"""Fixed: the ``catalog`` fixture is now function-scoped (the default), so
every test gets its own fresh list. State can no longer leak from a test
that mutates the catalog into whichever test runs next.
"""
import pytest

from src.inventory import add_item


@pytest.fixture
def catalog():
    # Function-scoped: a brand-new empty list is created for each test.
    return []


def test_add_item_appends_new_name(catalog):
    add_item(catalog, "widget")
    assert catalog == ["widget"]


def test_add_item_appends_multiple_names_in_order(catalog):
    add_item(catalog, "widget")
    add_item(catalog, "gadget")
    assert catalog == ["widget", "gadget"]


def test_catalog_starts_empty_for_a_fresh_scenario(catalog):
    # Now reliably true: the fixture hands out a fresh empty list every time,
    # regardless of test execution order.
    assert catalog == []
