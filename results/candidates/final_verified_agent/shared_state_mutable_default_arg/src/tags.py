"""Avoid the classic Python gotcha: a mutable default argument is created
ONCE, at function-definition time, and shared by every call that doesn't
pass its own list explicitly. Use ``None`` as a sentinel and build a fresh
list on each call instead.
"""


def add_tag(item, tags=None):
    if tags is None:
        tags = []
    if tags.count(item) == 0:
        tags.append(item)
    return tags
