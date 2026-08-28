"""Weighted sampling with an injectable RNG.

The RNG is a parameter so callers (and tests especially) can pass a
seeded ``random.Random`` instance and get deterministic results. Without
that, sampling rides on the global RNG's current state, and any test that
hardcodes "the" output of a random draw is really pinned to whatever seed
the run happens to start with -- a classic source of flaky tests.
"""
import random


def pick_weighted_sample(items, weights, k, rng=None):
    """Return k items drawn without replacement, biased by weight.

    ``rng`` may be any object exposing a ``choices`` method (e.g. an
    instance of ``random.Random``). It defaults to the global ``random``
    module.
    """
    if rng is None:
        rng = random
    pool = list(items)
    pool_weights = list(weights)
    chosen = []
    for _ in range(k):
        pick = rng.choices(pool, weights=pool_weights, k=1)[0]
        idx = pool.index(pick)
        pool.pop(idx)
        pool_weights.pop(idx)
        chosen.append(pick)
    return chosen
