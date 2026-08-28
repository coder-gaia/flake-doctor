"""Make this case's `src` package importable without installing it."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from src import config  # noqa: E402  (path must be set up first)


@pytest.fixture(autouse=True)
def _isolate_config():
    """Isolate the process-wide config cache and APP_MODE between tests.

    ``src.config.get_config()`` memoizes its result in a module global, and
    the config tests each mutate ``os.environ["APP_MODE"]``. pytest-randomly
    shuffles test order, so without this isolation a stale cached value (or a
    leaked env var) from an earlier test bleeds into a later one and the
    outcome becomes order-dependent.
    """
    saved_mode = os.environ.get("APP_MODE")
    config.reset_config()
    try:
        yield
    finally:
        config.reset_config()
        if saved_mode is None:
            os.environ.pop("APP_MODE", None)
        else:
            os.environ["APP_MODE"] = saved_mode
