"""These tests exercise src.config.get_config(), which caches its result in
a module-level global the first time it is called.

Without isolation the tests leak state into each other in two ways:
  * the cached config dict survives for the whole process, so whichever
    test calls get_config() first "wins"; and
  * mutations to os.environ["APP_MODE"] persist past the test that made
    them.

pytest-randomly shuffles test order between runs, so the leak showed up
as flakiness: test_config_honors_beta_mode_override passed when it ran
first and failed when test_config_defaults_to_production ran before it
and cached "production".

The autouse fixture gives every test a clean slate: a fresh (reset)
cache and a controlled APP_MODE environment variable.
"""
import pytest

from src import config
from src.config import get_config


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch):
    # Start each test with no APP_MODE and an empty cache...
    monkeypatch.delenv("APP_MODE", raising=False)
    config.reset_config()
    try:
        yield
    finally:
        # ...and don't leave a populated cache behind for the next test.
        config.reset_config()


def test_config_defaults_to_production(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)
    assert get_config()["mode"] == "production"


def test_config_honors_beta_mode_override(monkeypatch):
    monkeypatch.setenv("APP_MODE", "beta")
    assert get_config()["mode"] == "beta"


def test_config_is_cached_within_a_single_run(monkeypatch):
    monkeypatch.setenv("APP_MODE", "beta")
    first = get_config()
    # Changing the environment afterwards must not change an already
    # resolved config: the point of the cache is a stable value per run.
    monkeypatch.setenv("APP_MODE", "production")
    assert get_config() is first
    assert get_config()["mode"] == "beta"


def test_reset_config_forces_environment_reread(monkeypatch):
    monkeypatch.setenv("APP_MODE", "beta")
    assert get_config()["mode"] == "beta"
    monkeypatch.setenv("APP_MODE", "production")
    config.reset_config()
    assert get_config()["mode"] == "production"
