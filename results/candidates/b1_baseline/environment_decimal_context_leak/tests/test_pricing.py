"""Fixed: test_rounds_to_two_places_for_display now scopes its precision
change with decimal.localcontext() so it no longer leaks the reduced
precision into whichever test runs next. This makes the suite pass
reliably regardless of test execution order.
"""
from decimal import getcontext, localcontext

from src.pricing import unit_price


def test_rounds_to_two_places_for_display():
    with localcontext() as ctx:
        ctx.prec = 2  # scoped: restored automatically on block exit
        assert str(unit_price(10, 3)) == "3.3"


def test_full_precision_division():
    # With the precision change now scoped above, the default context
    # precision (28) is always in effect here, independent of order.
    assert str(unit_price(10, 3)) == "3.333333333333333333333333333"


def test_display_rounding_does_not_leak_precision():
    # Regression guard: running the display-rounding test must not alter
    # the global decimal context precision for subsequent tests.
    default_prec = getcontext().prec
    test_rounds_to_two_places_for_display()
    assert getcontext().prec == default_prec
    assert str(unit_price(10, 3)) == "3.333333333333333333333333333"
