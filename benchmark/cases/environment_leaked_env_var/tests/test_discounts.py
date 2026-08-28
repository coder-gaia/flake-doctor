"""Flaky because test_enables_beta_discount sets os.environ directly
(instead of monkeypatch.setenv, which auto-restores) and never cleans up
-- whichever test runs after it inherits the leaked variable.
"""
import os

from src.discounts import discount_for


def test_enables_beta_discount():
    os.environ["DISCOUNT_MODE"] = "beta"  # bug: should use monkeypatch
    assert discount_for(100.0) == 85.0


def test_default_mode_charges_full_price():
    # Bug in this test: assumes DISCOUNT_MODE is unset here. If
    # test_enables_beta_discount ran first and leaked "beta" into the
    # process environment, this test inherits it.
    assert discount_for(100.0) == 100.0
