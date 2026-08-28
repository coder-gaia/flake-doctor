"""Flaky because test_rounds_to_two_places_for_display mutates the global
decimal context precision directly (instead of the scoped
decimal.localcontext()) and never restores it -- whichever test runs
after it inherits the reduced precision.
"""
from decimal import getcontext

from src.pricing import unit_price


def test_rounds_to_two_places_for_display():
    getcontext().prec = 2  # bug: should use `with decimal.localcontext():`
    assert str(unit_price(10, 3)) == "3.3"


def test_full_precision_division():
    # Bug in this test: assumes the default context precision (28) is
    # still in effect. If test_rounds_to_two_places_for_display ran
    # first and left prec=2 behind, this test silently gets a truncated
    # result instead.
    assert str(unit_price(10, 3)) == "3.333333333333333333333333333"
