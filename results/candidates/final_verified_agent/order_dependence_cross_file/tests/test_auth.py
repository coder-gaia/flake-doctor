"""Coverage for the shared session store in src/auth.

``login`` used to mutate a process-wide dict with no cleanup, leaking VIP
state into whichever test ran next. conftest.py's autouse
``_isolate_session_store`` fixture now resets the store around every test;
these tests verify the login / is_vip behaviour itself.
"""
from src.auth import is_vip, login, logout, reset_sessions


def test_login_marks_user_as_vip():
    login("user-42", is_vip=True)
    assert is_vip("user-42") is True


def test_login_defaults_to_non_vip():
    login("user-1")
    assert is_vip("user-1") is False


def test_unknown_user_is_not_vip():
    assert is_vip("never-seen") is False


def test_logout_clears_single_user():
    login("user-2", is_vip=True)
    logout("user-2")
    assert is_vip("user-2") is False


def test_reset_sessions_clears_all_state():
    login("user-3", is_vip=True)
    login("user-4", is_vip=True)
    reset_sessions()
    assert is_vip("user-3") is False
    assert is_vip("user-4") is False


def test_sessions_do_not_leak_between_tests():
    # Relies on the autouse isolation fixture: no prior test's login should
    # still be visible here.
    assert is_vip("user-42") is False
