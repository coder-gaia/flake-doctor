"""Behavioural coverage for src/billing.price_for.

The historical flake here was caused by leaked session state from
test_auth.py (see conftest.py's autouse ``_isolate_session_store`` fixture,
which now guarantees every test starts with an empty session store).

These tests also pin down the actual pricing behaviour so a regression in
the discount logic is caught rather than silently passing.
"""
from src.auth import login
from src.billing import VIP_DISCOUNT, price_for


def test_new_user_pays_full_price():
    # A brand-new user with no session must never receive a discount.
    assert price_for("user-42", 100.0) == 100.0


def test_unknown_user_pays_full_price():
    assert price_for("someone-who-never-logged-in", 250.0) == 250.0


def test_logged_in_non_vip_pays_full_price():
    login("user-7", is_vip=False)
    assert price_for("user-7", 100.0) == 100.0


def test_vip_user_gets_discounted_price():
    login("user-42", is_vip=True)
    assert price_for("user-42", 100.0) == 80.0


def test_vip_discount_constant_is_twenty_percent():
    assert VIP_DISCOUNT == 0.20


def test_vip_price_is_rounded_to_cents():
    login("user-9", is_vip=True)
    # 49.99 * (1 - 0.20) == 39.992 -> rounded to 39.99
    assert price_for("user-9", 49.99) == 39.99
