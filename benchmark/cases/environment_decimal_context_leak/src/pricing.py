"""Pricing math using Python's global decimal context precision."""
from decimal import Decimal


def unit_price(total, quantity):
    return Decimal(total) / Decimal(quantity)
