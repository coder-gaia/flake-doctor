"""A tiny in-memory inventory list."""


def add_item(catalog, name):
    if name not in catalog:
        catalog.append(name)
    return catalog
