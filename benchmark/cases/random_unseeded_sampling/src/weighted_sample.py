"""Weighted sampling on the global `random` module.

No injectable RNG here -- a common real-world source of flaky tests, since
any test that hardcodes "the" output of a random draw is really pinned to
whatever the global RNG's current state happens to produce.
"""
import random


def pick_weighted_sample(items, weights, k):
    """Return k items drawn without replacement, biased by weight."""
    pool = list(items)
    pool_weights = list(weights)
    chosen = []
    for _ in range(k):
        pick = random.choices(pool, weights=pool_weights, k=1)[0]
        idx = pool.index(pick)
        pool.pop(idx)
        pool_weights.pop(idx)
        chosen.append(pick)
    return chosen
