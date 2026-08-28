"""Precision tests for pricing math.

Historically these tests were flaky under randomized ordering:
``test_rounds_to_two_places_for_display`` mutated the *global* decimal
context (``getcontext().prec = 2``) and never restored it, so whichever
test ran afterwards inherited the reduced precision. The fix is to scope
the precision change with ``decimal.localcontext()`` so nothing leaks.
"""
from decimal import getcontext, localcontext

from src.pricing import unit_price


def test_rounds_to_two_places_for_display():
    # Scope the precision change so it cannot leak into other tests.
    with localcontext() as ctx:
        ctx.prec = 2
        assert str(unit_price(10, 3)) == "3.3"


def test_full_precision_division():
    # With no leaked global state, the default context precision (28)
    # is in effect and the division keeps full precision.
    assert str(unit_price(10, 3)) == "3.333333333333333333333333333"


def test_global_context_precision_is_not_mutated():
    # Guard against regressions: the display-rounding test must not
    # change the process-wide decimal precision.
    assert getcontext().prec == 28
