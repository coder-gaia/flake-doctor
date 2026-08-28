"""Previously flaky because get_config() caches its result in a module-level
global the first time it's called -- whichever test called it first "won"
for the rest of the process.

The fix: reload the config module before each test so the cache starts
empty, and control the APP_MODE environment variable explicitly. Tests now
always call ``config.get_config()`` through the (possibly reloaded) module
object rather than a stale imported reference, so ordering no longer matters.
"""
import importlib

import pytest

from src import config


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    """Give every test a pristine config module with no cached result."""
    monkeypatch.delenv("APP_MODE", raising=False)
    importlib.reload(config)
    yield
    # Leave the module in a clean state for anything that runs later.
    monkeypatch.delenv("APP_MODE", raising=False)
    importlib.reload(config)


def test_config_defaults_to_production(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)
    importlib.reload(config)
    assert config.get_config()["mode"] == "production"


def test_config_honors_beta_mode_override(monkeypatch):
    monkeypatch.setenv("APP_MODE", "beta")
    importlib.reload(config)
    assert config.get_config()["mode"] == "beta"


def test_config_caches_first_result_within_a_process(monkeypatch):
    monkeypatch.setenv("APP_MODE", "beta")
    importlib.reload(config)

    first = config.get_config()
    assert first["mode"] == "beta"

    # Changing the environment after the first call must not change the
    # already-cached result -- that caching behavior is intentional.
    monkeypatch.setenv("APP_MODE", "production")
    assert config.get_config()["mode"] == "beta"
    assert config.get_config() is first
