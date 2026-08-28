"""Reliable tests for ``pick_weighted_sample``.

The original assertion bet against the current run's RNG seed.  ``pytest-randomly``
reseeds Python's ``random`` module with a fresh, unrelated seed before every test,
so "gold is drawn first" was true only for *some* seeds (~7 runs in 8).

Instead of asserting one exact draw, we verify the property the function really
guarantees: over many draws a heavily weighted item dominates by a margin so
large that no seed can break it, plus a few structural checks that hold for
every seed.
"""
import random
from collections import Counter

from src.weighted_sample import pick_weighted_sample


def _draw_counts(items, weights, k=1, trials=5000):
    """Run many independent draws and tally how often each item appears."""
    counter = Counter()
    for _ in range(trials):
        counter.update(pick_weighted_sample(items, weights, k=k))
    return counter


def test_heavily_weighted_item_is_picked_first():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]  # "gold" dominates: p ~= 20/23 ~= 0.87 per draw

    trials = 5000
    counts = _draw_counts(items, weights, k=1, trials=trials)

    # Every result is exactly one valid item.
    assert set(counts) <= set(items)
    assert sum(counts.values()) == trials

    # "gold" wins the vast majority of draws.  Expected share ~87%; this 70%
    # lower bound sits tens of standard deviations away from the mean, so it
    # holds for every seed pytest-randomly can choose.
    assert counts["gold"] > 0.70 * trials

    # ...and it is picked strictly more often than each lighter item.
    for other in ("silver", "bronze", "wood"):
        assert counts["gold"] > counts[other]


def test_equal_weights_give_roughly_uniform_draws():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [1, 1, 1, 1]

    trials = 8000
    counts = _draw_counts(items, weights, k=1, trials=trials)

    assert sum(counts.values()) == trials
    for item in items:
        # Expected share 25%; generous 15%-35% band tolerates any seed.
        assert 0.15 * trials < counts[item] < 0.35 * trials


def test_zero_weight_items_are_never_picked():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [1, 0, 0, 0]

    counts = _draw_counts(items, weights, k=1, trials=2000)

    assert counts["gold"] == 2000
    assert counts["silver"] == 0
    assert counts["bronze"] == 0
    assert counts["wood"] == 0


def test_result_shape_is_stable_across_seeds():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]

    for seed in range(50):
        random.seed(seed)
        result = pick_weighted_sample(items, weights, k=2)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(item in items for item in result)
