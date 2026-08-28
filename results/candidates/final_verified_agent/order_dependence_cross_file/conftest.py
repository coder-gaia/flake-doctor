"""Make this case's `src` package importable without installing it."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def _isolate_session_store():
    """Guarantee every test starts and ends with an empty session store.

    ``src.auth`` keeps sessions in a module-level dict that persists for the
    whole process. Without this reset, a test that calls ``login`` leaks VIP
    state into whatever test runs next (order is randomised by
    pytest-randomly), which is what made ``test_new_user_pays_full_price``
    flaky.
    """
    from src.auth import reset_sessions

    reset_sessions()
    try:
        yield
    finally:
        reset_sessions()
