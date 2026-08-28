"""A tiny in-memory inventory list."""


def add_item(catalog, name):
    # MUTANT: no longer checks for duplicates before appending.
    catalog.append(name)
    return catalog
