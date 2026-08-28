"""The class under test has a subtle bug: ``Cart.items`` is defined at the
class level, so every ``Cart()`` instance shares the *same* underlying list.
Without isolation, items added by one test leak into carts created by later
tests, which makes assertions about "a brand-new cart" order-dependent and
flaky.

The autouse fixture below rebinds ``Cart.items`` to a fresh, empty list
before and after every test, guaranteeing each test starts from a clean,
predictable state regardless of execution order.
"""
import pytest

from src.cart import Cart


@pytest.fixture(autouse=True)
def _isolate_shared_cart_state():
    # Reset the shared class-level list so no test can inherit items that
    # were added by whichever test happened to run first.
    Cart.items = []
    yield
    Cart.items = []


def test_new_cart_starts_empty():
    cart = Cart()
    assert cart.total() == 0.0


def test_cart_totals_a_single_item():
    cart = Cart()
    cart.add("widget", price=9.99, qty=2)
    assert cart.total() == 19.98


def test_cart_totals_multiple_items():
    cart = Cart()
    cart.add("widget", price=9.99, qty=2)
    cart.add("gadget", price=4.00, qty=3)
    assert cart.total() == pytest.approx(31.98)


def test_carts_do_not_share_items_within_a_test():
    first = Cart()
    first.add("widget", price=9.99, qty=2)

    second = Cart()
    # A cart created after another cart has had items added must still be
    # independent; this only holds once the shared-state bug is handled.
    assert second.total() == 0.0
