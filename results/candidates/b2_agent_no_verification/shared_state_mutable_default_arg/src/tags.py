"""Classic Python gotcha: a mutable default argument is created ONCE, at
function-definition time, and shared by every call that doesn't pass its
own list explicitly.

The fix is to use a sentinel default (``None``) and build a fresh list
inside the function on every call that doesn't supply one.
"""


def add_tag(item, tags=None):
    if tags is None:
        tags = []
    if tags.count(item) == 0:
        tags.append(item)
    return tags
