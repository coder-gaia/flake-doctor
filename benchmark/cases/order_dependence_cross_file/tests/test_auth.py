"""The actual culprit. This test always passes on its own -- the bug is
what it leaves behind: `login` mutates the shared, module-level `_SESSIONS`
dict in src/auth.py and nothing ever resets it. Whoever runs after this
test inherits its session state.
"""
from src.auth import login


def test_login_marks_user_as_vip():
    login("user-42", is_vip=True)
    assert True  # this file's own assertion never fails
