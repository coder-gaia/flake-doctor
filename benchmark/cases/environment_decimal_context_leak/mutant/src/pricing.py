"""Pricing math using Python's global decimal context precision."""
from decimal import Decimal


def unit_price(total, quantity):
    # MUTANT: operands swapped.
    return Decimal(quantity) / Decimal(total)
