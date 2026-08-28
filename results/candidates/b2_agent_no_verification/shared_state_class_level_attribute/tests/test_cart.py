"""Each Cart instance owns its own item list, so these tests pass
regardless of execution order.
"""
from src.cart import Cart


def test_new_cart_starts_empty():
    cart = Cart()
    assert cart.total() == 0.0


def test_cart_totals_a_single_item():
    cart = Cart()
    cart.add("widget", price=9.99, qty=2)
    assert cart.total() == 19.98


def test_carts_do_not_share_items():
    first = Cart()
    first.add("widget", price=9.99, qty=2)
    second = Cart()
    assert second.total() == 0.0
    assert first.total() == 19.98
