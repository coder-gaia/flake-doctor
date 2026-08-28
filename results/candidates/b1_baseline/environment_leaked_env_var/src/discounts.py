"""Discount logic driven by an environment feature flag."""
import os


def discount_for(amount):
    mode = os.environ.get("DISCOUNT_MODE", "stable")
    if mode == "beta":
        return round(amount * 0.85, 2)
    return amount
