"""Each test gets its own fresh ``catalog`` list.

The fixture is function-scoped (the default), so mutations made by one test
cannot leak into another regardless of the order tests run in.
"""
import pytest

from src.inventory import add_item


@pytest.fixture
def catalog():
    # Function-scoped: a brand new list is created for every test that uses it.
    return []


def test_add_item_appends_new_name(catalog):
    add_item(catalog, "widget")
    assert catalog == ["widget"]


def test_catalog_starts_empty_for_a_fresh_scenario(catalog):
    # `catalog` is function-scoped, so it always starts empty here no matter
    # what other tests ran first.
    assert catalog == []


def test_add_item_returns_the_same_catalog_object(catalog):
    result = add_item(catalog, "widget")
    assert result is catalog


def test_add_item_does_not_add_duplicate_names(catalog):
    add_item(catalog, "widget")
    add_item(catalog, "widget")
    assert catalog == ["widget"]


def test_add_item_preserves_insertion_order_for_distinct_names(catalog):
    add_item(catalog, "widget")
    add_item(catalog, "gadget")
    add_item(catalog, "gizmo")
    assert catalog == ["widget", "gadget", "gizmo"]


def test_add_item_appends_to_a_non_empty_catalog(catalog):
    add_item(catalog, "widget")
    add_item(catalog, "gadget")
    assert catalog == ["widget", "gadget"]


def test_add_item_allows_readding_after_a_removed_name(catalog):
    add_item(catalog, "widget")
    catalog.remove("widget")
    add_item(catalog, "widget")
    assert catalog == ["widget"]
