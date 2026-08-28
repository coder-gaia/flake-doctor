"""Flaky because it asserts an exact draw from the global RNG.

pytest-randomly reseeds Python's `random` module with a fresh, unrelated
seed before every test -- that's the point of the plugin, it exists to
surface exactly this kind of bug. "Heavily weighted" is not "guaranteed".
"""
from src.weighted_sample import pick_weighted_sample


def test_heavily_weighted_item_is_picked_first():
    items = ["gold", "silver", "bronze", "wood"]
    weights = [20, 1, 1, 1]  # "gold" should dominate the draw

    result = pick_weighted_sample(items, weights, k=1)

    # Bug in this test: roughly one run in eight still draws a different
    # item, and this assertion is really a bet against the current run's
    # seed rather than a check on the sampling logic.
    assert result == ["gold"]
