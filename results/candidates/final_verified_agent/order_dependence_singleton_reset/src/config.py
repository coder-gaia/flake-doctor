"""A naive config loader that caches its result process-wide."""
import os

_config = None


def get_config():
    global _config
    if _config is None:
        _config = {"mode": os.environ.get("APP_MODE", "production")}
    return _config


def reset_config():
    """Discard the process-wide cache so the next get_config() re-reads env.

    The cache is a deliberate optimization, but without a way to invalidate
    it the value observed depends on which caller ran first. This lets tests
    (or long-running processes that need to reload) start from a clean slate.
    """
    global _config
    _config = None
