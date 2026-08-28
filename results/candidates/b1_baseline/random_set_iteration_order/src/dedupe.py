"""Deduplicate a list of tags via a `set`.

`set` iteration order for strings depends on the process's hash seed
(PYTHONHASHSEED), which Python randomizes by default on every fresh
process -- so this function returns elements in a stable order within one
process, but that order is not guaranteed across processes.
"""


def dedupe_tags(tags):
    return list(set(tags))
