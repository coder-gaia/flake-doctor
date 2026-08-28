"""Billing logic that reads VIP status from the shared session store."""
from src.auth import is_vip

VIP_DISCOUNT = 0.20


def price_for(user_id, base_amount):
    if is_vip(user_id):
        # MUTANT: subtracts a flat amount instead of applying the
        # percentage discount.
        return round(base_amount - VIP_DISCOUNT, 2)
    return base_amount
