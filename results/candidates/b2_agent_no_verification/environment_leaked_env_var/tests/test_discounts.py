"""Tests for the DISCOUNT_MODE feature flag.

Each test that depends on DISCOUNT_MODE now manages it through pytest's
``monkeypatch`` fixture, which restores the original environment after the
test finishes. This keeps the process environment from leaking between
tests regardless of execution order.
"""
from src.discounts import discount_for


def test_enables_beta_discount(monkeypatch):
    monkeypatch.setenv("DISCOUNT_MODE", "beta")
    assert discount_for(100.0) == 85.0


def test_default_mode_charges_full_price(monkeypatch):
    # Explicitly assert the default (no beta flag) behaviour, independent of
    # whatever any other test may have set in the environment.
    monkeypatch.delenv("DISCOUNT_MODE", raising=False)
    assert discount_for(100.0) == 100.0
