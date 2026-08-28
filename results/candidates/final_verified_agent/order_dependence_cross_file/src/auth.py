"""Minimal session store shared across the app."""

_SESSIONS = {}


def login(user_id, *, is_vip=False):
    """Log a user in, recording VIP status in the shared session store."""
    _SESSIONS[user_id] = {"is_vip": is_vip}


def logout(user_id) -> None:
    """Remove a single user's session from the shared store."""
    _SESSIONS.pop(user_id, None)


def reset_sessions() -> None:
    """Clear the entire shared session store (useful for test isolation)."""
    _SESSIONS.clear()


def is_vip(user_id) -> bool:
    return _SESSIONS.get(user_id, {}).get("is_vip", False)
