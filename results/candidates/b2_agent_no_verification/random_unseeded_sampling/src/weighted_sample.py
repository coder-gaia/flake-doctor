"""Weighted sampling with an injectable RNG.

Callers that care about reproducibility (tests, above all) can pass their own
``random.Random`` instance via ``rng``. When they don't, we fall back to the
process-global ``random`` module so existing callers keep working. Hardcoding
"the" output of a draw against the global RNG is a classic source of flaky
tests -- it pins the assertion to whatever seed the run happens to start with.
"""
import random


def pick_weighted_sample(items, weights, k, rng=None):
    """Return k items drawn without replacement, biased by weight.

    ``rng`` may be any object exposing ``choices`` like a ``random.Random``
    instance; if omitted, the global ``random`` module is used.
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
