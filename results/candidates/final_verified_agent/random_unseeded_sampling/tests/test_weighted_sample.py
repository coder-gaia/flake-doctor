"""Deterministic tests for weighted sampling.

The old version of ``test_heavily_weighted_item_is_picked_first`` asserted
an exact draw from the *global* ``random`` module. pytest-randomly reseeds
that module with a fresh, unrelated seed before every test, so roughly one
run in eight legitimately drew a non-"gold" item and the exact-equality
assertion failed -- a bet against the run's seed, not a check on the code.

The fix: inject a seeded RNG so the draw is reproducible. A separate
statistical test exercises the actual weighting behaviour across many
draws without pinning to a single lucky seed.
"""
import random

from src.weighted_sample import pick_weighted_sample


def test_heavily_weighted_item_is_picked_first():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]  # "gold" should dominate the draw

    # Inject a seeded RNG: the result no longer depends on whatever seed
    # the test run started with, so this is now a stable check on the
    # sampling logic rather than a bet against the current seed.
    rng = random.Random(0)
    result = pick_weighted_sample(items, weights, k=1, rng=rng)

    assert result == ["gold"]


def test_weighting_biases_draws_toward_heavy_item():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]  # gold ~ 20/23 ~ 87% of first draws

    rng = random.Random(20260828)
    trials = 5000
    gold_first = sum(
        pick_weighted_sample(items, weights, k=1, rng=rng) == ["gold"]
        for _ in range(trials)
    )

    # Expected ~0.87; allow a wide margin so this stays deterministic-safe
    # while still failing if the weighting is ignored (which would give
    # ~0.25) or inverted.
    assert 0.80 < gold_first / trials < 0.93


def test_sample_is_without_replacement_and_full_permutation():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]

    rng = random.Random(1)
    result = pick_weighted_sample(items, weights, k=4, rng=rng)

    assert sorted(result) == sorted(items)
    assert len(set(result)) == 4


def test_default_rng_uses_global_random_module():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]

    random.seed(0)
    result = pick_weighted_sample(items, weights, k=1)

    assert result == ["gold"]
