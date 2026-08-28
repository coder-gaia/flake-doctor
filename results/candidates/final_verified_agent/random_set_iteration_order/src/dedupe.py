"""Deduplicate a list of tags while preserving first-seen order.

Using ``list(set(tags))`` loses ordering: ``set`` iteration order for
strings depends on the process's hash seed (``PYTHONHASHSEED``), which
Python randomizes on every fresh process. That makes the result unstable
across processes.

``dict.fromkeys`` removes duplicates while keeping the order in which each
element was first encountered, which is both deterministic and the
behaviour callers expect.
"""


def dedupe_tags(tags):
    return list(dict.fromkeys(tags))
