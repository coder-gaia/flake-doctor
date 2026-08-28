"""Deterministic weighted-sampling tests.

The old version of this test asserted an exact draw from the *global* RNG.
pytest-randomly reseeds Python's `random` module with a fresh, unrelated seed
before every test, so roughly one run in eight drew a different item and the
assertion failed -- it was betting against the run's seed rather than checking
the sampling logic.

`pick_weighted_sample` now accepts an injectable `rng`, so these tests seed
their own `random.Random` instance and are reproducible no matter what the
process-wide RNG state happens to be.
"""
import random

from src.weighted_sample import pick_weighted_sample


def test_heavily_weighted_item_is_picked_first():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]  # "gold" should dominate the draw

    # A fixed, local seed makes this single draw reproducible regardless of
    # the global RNG state that pytest-randomly reseeds per test.
    rng = random.Random(0)

    result = pick_weighted_sample(items, weights, k=1, rng=rng)

    assert result == ["gold"]


def test_heavy_weight_dominates_across_many_draws():
    """The statistical property the old test was really trying to express."""
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]

    rng = random.Random(12345)
    first_picks = [
        pick_weighted_sample(items, weights, k=1, rng=rng)[0]
        for _ in range(2000)
    ]

    gold_fraction = first_picks.count("gold") / len(first_picks)
    # Expected share is 20/23 ~= 0.87; each light item is ~0.043.
    assert gold_fraction > 0.8
    # Every item stays reachable -- weighting biases, it doesn't exclude.
    assert set(first_picks) == set(items)


def test_sample_is_without_replacement():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]

    rng = random.Random(7)
    result = pick_weighted_sample(items, weights, k=4, rng=rng)

    assert sorted(result) == sorted(items)


def test_default_rng_falls_back_to_global_module():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]

    random.seed(0)
    result = pick_weighted_sample(items, weights, k=1)

    assert result == ["gold"]
