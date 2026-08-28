"""Previously flaky: this test is the innocent bystander. The real bug is
that test_auth.py's test_login_marks_user_as_vip leaks shared session
state by logging in a hard-coded user_id ("user-42") as VIP. Whenever that
test ran first, "user-42" was already a VIP here and got a discount, so the
full-price assertion failed.

Fix: don't depend on the global state of any particular hard-coded user id.
Generate a guaranteed-fresh user id for this test so the "brand-new user"
precondition is always true, regardless of test ordering.
"""
import uuid

from src.billing import price_for


def _fresh_user_id():
    """Return a user id that no other test could have touched."""
    return f"user-{uuid.uuid4()}"


def test_new_user_pays_full_price():
    # Use a brand-new, unique user id so this test never observes VIP
    # state leaked in from test_auth.py (or anywhere else).
    new_user = _fresh_user_id()
    assert price_for(new_user, 100.0) == 100.0


def test_new_user_pays_full_price_is_order_independent():
    # Extra guard: even calling price_for repeatedly for distinct fresh
    # users must keep returning full price, proving no cross-user leakage.
    for _ in range(5):
        assert price_for(_fresh_user_id(), 250.0) == 250.0
