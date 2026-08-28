"""Fixed by never relying on add_tag's mutable default argument.

add_tag's default `tags=[]` is a single list object created once at
import time and shared by every call site that omits the argument. Any
test that leaned on that default would observe tags left behind by
earlier tests, making the suite order-dependent and therefore flaky when
rerun.

Every test below now passes its own freshly created list, so the calls
are fully isolated from one another regardless of execution order.
"""
from src.tags import add_tag


def test_add_tag_to_a_fresh_item():
    result = add_tag("urgent", [])
    assert result == ["urgent"]


def test_add_tag_starts_from_an_empty_list():
    # Pass an explicit, brand-new list so this call cannot observe
    # anything a previous call appended to the shared mutable default.
    result = add_tag("billing", [])
    assert result == ["billing"]


def test_add_tag_appends_to_an_existing_list():
    result = add_tag("payment", ["billing"])
    assert result == ["billing", "payment"]


def test_add_tag_calls_are_independent_when_given_fresh_lists():
    first = add_tag("a", [])
    second = add_tag("b", [])
    assert first == ["a"]
    assert second == ["b"]
