"""Decimal precision must be changed in a scoped way.

`test_rounds_to_two_places_for_display` needs a reduced precision only for
its own assertion, so it uses `decimal.localcontext()`, which restores the
previous context on exit. Mutating `getcontext().prec` directly would leak
the reduced precision into whatever test runs next (pytest-randomly shuffles
the order), making `test_full_precision_division` flaky.
"""
from decimal import localcontext

from src.pricing import unit_price


def test_rounds_to_two_places_for_display():
    with localcontext() as ctx:
        ctx.prec = 2
        assert str(unit_price(10, 3)) == "3.3"


def test_full_precision_division():
    # Bug in this test: assumes the default context precision (28) is
    # still in effect. If test_rounds_to_two_places_for_display ran
    # first and left prec=2 behind, this test silently gets a truncated
    # result instead.
    assert str(unit_price(10, 3)) == "3.333333333333333333333333333"
