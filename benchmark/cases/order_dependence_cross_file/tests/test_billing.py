"""Looks flaky in isolation, but it is the innocent bystander -- see
case.yaml. The real bug lives in test_auth.py, which leaks shared session
state into whichever test runs after it.
"""
from src.billing import price_for


def test_new_user_pays_full_price():
    # Bug in the test suite (not in this file): whether "user-42" is a
    # brand-new user with no VIP discount depends entirely on whether
    # test_auth.py's test_login_marks_user_as_vip happened to run first
    # and already logged this same user_id in as VIP.
    assert price_for("user-42", 100.0) == 100.0
