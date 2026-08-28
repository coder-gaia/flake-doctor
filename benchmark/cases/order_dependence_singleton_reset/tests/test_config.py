"""Flaky because get_config() caches its result in a module-level global
the first time it's called -- whichever test calls it first "wins" for
the rest of the process, regardless of what a later test sets up.
"""
import os

from src.config import get_config


def test_config_defaults_to_production():
    os.environ.pop("APP_MODE", None)
    assert get_config()["mode"] == "production"


def test_config_honors_beta_mode_override():
    os.environ["APP_MODE"] = "beta"
    # Bug in this test: assumes get_config() re-reads the environment every
    # call. If test_config_defaults_to_production already ran and cached
    # "production", this test observes that stale cached value instead.
    assert get_config()["mode"] == "beta"
