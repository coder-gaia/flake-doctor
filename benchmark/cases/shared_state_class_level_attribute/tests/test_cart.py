"""Flaky because Cart.items is a class-level list -- every Cart() instance
shares the exact same list object, so a cart built in one test can carry
items left behind by whichever test ran before it.
"""
from src.cart import Cart


def test_new_cart_starts_empty():
    cart = Cart()
    # Bug in this test: assumes a brand-new Cart() has no items. True only
    # if no earlier test has ever called .add() on any Cart instance.
    assert cart.total() == 0.0


def test_cart_totals_a_single_item():
    cart = Cart()
    cart.add("widget", price=9.99, qty=2)
    assert cart.total() == 19.98
