"""Each test controls DISCOUNT_MODE through monkeypatch so the change is
scoped to that test and automatically restored afterwards.

Previously test_enables_beta_discount mutated os.environ directly and
never cleaned up. pytest-randomly shuffles test order between runs, so
whenever test_enables_beta_discount happened to run first the leaked
"beta" value was inherited by test_default_mode_charges_full_price,
making it fail intermittently.
"""
from src.discounts import discount_for


def test_enables_beta_discount(monkeypatch):
    monkeypatch.setenv("DISCOUNT_MODE", "beta")
    assert discount_for(100.0) == 85.0


def test_default_mode_charges_full_price(monkeypatch):
    # Pin the precondition explicitly instead of relying on ambient
    # process state: with no DISCOUNT_MODE set there is no discount.
    monkeypatch.delenv("DISCOUNT_MODE", raising=False)
    assert discount_for(100.0) == 100.0
