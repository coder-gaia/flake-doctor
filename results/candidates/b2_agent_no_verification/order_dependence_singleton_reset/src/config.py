"""A naive config loader that caches its result process-wide."""
import os

_config = None


def get_config():
    global _config
    if _config is None:
        _config = {"mode": os.environ.get("APP_MODE", "production")}
    return _config


def reset_config():
    """Invalidate the process-wide cache so the next get_config() call
    re-reads the environment.

    Useful for tests (which need isolation from one another) and for any
    code that changes APP_MODE at runtime and needs the change to take
    effect.
    """
    global _config
    _config = None
