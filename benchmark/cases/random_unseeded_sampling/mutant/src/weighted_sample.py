"""Weighted sampling on the global `random` module.

No injectable RNG here -- a common real-world source of flaky tests, since
any test that hardcodes "the" output of a random draw is really pinned to
whatever the global RNG's current state happens to produce.
"""
import random


def pick_weighted_sample(items, weights, k):
    """Return k items drawn without replacement, biased by weight."""
    pool = list(items)
    chosen = []
    for _ in range(k):
        # MUTANT: weights are accepted but never used -- every item is
        # equally likely regardless of its weight.
        pick = random.choice(pool)
        pool.remove(pick)
        chosen.append(pick)
    return chosen
