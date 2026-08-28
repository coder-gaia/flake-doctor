"""Deduplicate a list of tags while preserving first-occurrence order.

Using ``list(set(tags))`` would drop duplicates but return elements in an
order that depends on the process hash seed (``PYTHONHASHSEED``), which
Python randomizes per process. That makes the result non-deterministic
across processes.

``dict.fromkeys`` keeps the first occurrence of each element and preserves
insertion order, so the output is stable and predictable.
"""


def dedupe_tags(tags):
    return list(dict.fromkeys(tags))
