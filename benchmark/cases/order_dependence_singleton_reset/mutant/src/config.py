"""A naive config loader that caches its result process-wide."""
import os

_config = None


def get_config():
    global _config
    if _config is None:
        # MUTANT: wrong default value when APP_MODE is unset.
        _config = {"mode": os.environ.get("APP_MODE", "staging")}
    return _config
