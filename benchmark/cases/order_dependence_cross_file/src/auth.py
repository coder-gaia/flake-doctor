"""Minimal session store shared across the app."""

_SESSIONS = {}


def login(user_id, *, is_vip=False):
    """Log a user in, recording VIP status in the shared session store."""
    _SESSIONS[user_id] = {"is_vip": is_vip}


def is_vip(user_id) -> bool:
    return _SESSIONS.get(user_id, {}).get("is_vip", False)
