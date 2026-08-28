"""Billing logic that reads VIP status from the shared session store."""
from src.auth import is_vip

VIP_DISCOUNT = 0.20


def price_for(user_id, base_amount):
    if is_vip(user_id):
        return round(base_amount * (1 - VIP_DISCOUNT), 2)
    return base_amount
