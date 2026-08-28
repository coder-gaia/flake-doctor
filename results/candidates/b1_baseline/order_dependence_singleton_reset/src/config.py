"""A naive config loader that caches its result process-wide."""
import os

_config = None


def get_config():
    global _config
    if _config is None:
        _config = {"mode": os.environ.get("APP_MODE", "production")}
    return _config
