"""Make this case's `src` package importable without installing it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest


@pytest.fixture(autouse=True)
def _isolate_session_store():
    """Guarantee every test starts and ends with an empty session store.

    ``src.auth`` keeps sessions in a module-level ``_SESSIONS`` dict that lives
    for the whole test process. Without this fixture, a test that logs a user
    in (e.g. ``test_login_marks_user_as_vip``) leaks that state into whichever
    test happens to run next, making order-dependent tests flaky.
    """
    from src import auth

    auth.reset_sessions()
    try:
        yield
    finally:
        auth.reset_sessions()
