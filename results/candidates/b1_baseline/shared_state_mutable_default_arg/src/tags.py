"""Classic Python gotcha: a mutable default argument is created ONCE, at
function-definition time, and shared by every call that doesn't pass its
own list explicitly.
"""


def add_tag(item, tags=[]):
    if tags.count(item) == 0:
        tags.append(item)
    return tags
