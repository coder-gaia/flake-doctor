"""Fixed: use monkeypatch to set/unset DISCOUNT_MODE so nothing leaks
between tests. monkeypatch.setenv auto-restores the previous value (or
removes the variable) during teardown, and monkeypatch.delenv guarantees
the default-mode test sees a clean environment regardless of run order.
"""
from src.discounts import discount_for


def test_enables_beta_discount(monkeypatch):
    monkeypatch.setenv("DISCOUNT_MODE", "beta")
    assert discount_for(100.0) == 85.0


def test_default_mode_charges_full_price(monkeypatch):
    monkeypatch.delenv("DISCOUNT_MODE", raising=False)
    assert discount_for(100.0) == 100.0
