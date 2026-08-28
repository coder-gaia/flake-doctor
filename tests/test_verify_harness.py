"""Integration tests for flakedoctor's own detection and verification
harness, exercised against the timing_ttl_second_boundary benchmark case.

These are not benchmark cases -- they test the oracle itself. A good fix
must pass all four gates; each cheat variant below is designed to trip
exactly one specific gate, proving that gate actually does its job rather
than passing by coincidence.
"""
import shutil
from pathlib import Path

from flakedoctor.verify import verify_fix

CASE_DIR = Path(__file__).resolve().parents[1] / "benchmark" / "cases" / "timing_ttl_second_boundary"
TARGET_TEST = "tests/test_ttl_cache.py::test_set_then_get_within_ttl"

GOOD_FIX = '''"""Deterministic clock: no more randomness, no more boundary luck.

Split into two tests on purpose -- the same-bucket happy path keeps the
original name and behavior, and a new test makes expiry an explicit,
checked behavior instead of an untested assumption.
"""
from src.ttl_cache import TTLCache


def test_set_then_get_within_ttl():
    ticks = iter([1000.1, 1000.2])
    cache = TTLCache(ttl_seconds=1, clock=lambda: next(ticks))
    cache.set("session", "alice")
    assert cache.get("session") == "alice"


def test_entry_expires_in_a_new_bucket():
    ticks = iter([1000.1, 1002.5])
    cache = TTLCache(ttl_seconds=1, clock=lambda: next(ticks))
    cache.set("session", "alice")
    assert cache.get("session") is None
'''

SLEEP_MASKED_FIX = '''"""Cheats by sleeping until safely inside a bucket instead of removing
the randomness -- exactly what V3's forbidden-call scan exists to catch.
"""
import random
import time

from src.ttl_cache import TTLCache


def test_set_then_get_within_ttl():
    time.sleep(0.01)
    start = 1000.5 + random.uniform(-0.01, 0.01)
    ticks = iter([start, start + 0.001])
    cache = TTLCache(ttl_seconds=1, clock=lambda: next(ticks))
    cache.set("session", "alice")
    assert cache.get("session") == "alice"
'''

SKIPPED_FIX = '''"""Cheats by skipping instead of fixing."""
import pytest


@pytest.mark.skip(reason="flaky, investigating")
def test_set_then_get_within_ttl():
    assert False
'''

WEAKENED_FIX = '''"""Cheats by weakening the assertion into something that can never
fail, regardless of what TTLCache actually does."""
from src.ttl_cache import TTLCache


def test_set_then_get_within_ttl():
    cache = TTLCache(ttl_seconds=1)
    assert cache is not None
'''


def _make_candidate(tmp_path, test_source: str) -> Path:
    candidate = tmp_path / "candidate"
    shutil.copytree(CASE_DIR, candidate)
    (candidate / "tests" / "test_ttl_cache.py").write_text(test_source, encoding="utf-8")
    return candidate


def test_good_fix_passes_all_four_gates(tmp_path):
    candidate = _make_candidate(tmp_path, GOOD_FIX)
    report = verify_fix(CASE_DIR, candidate, TARGET_TEST, reruns=20)
    assert report.all_passed, report.as_feedback()


def test_sleep_based_masking_fails_anti_cheat(tmp_path):
    candidate = _make_candidate(tmp_path, SLEEP_MASKED_FIX)
    report = verify_fix(CASE_DIR, candidate, TARGET_TEST, reruns=20)
    failing = {g.name for g in report.failing()}
    assert "anti_cheat" in failing, report.as_feedback()


def test_skip_marker_fails_stability_and_anti_cheat(tmp_path):
    candidate = _make_candidate(tmp_path, SKIPPED_FIX)
    report = verify_fix(CASE_DIR, candidate, TARGET_TEST, reruns=5)
    failing = {g.name for g in report.failing()}
    assert "stability" in failing, report.as_feedback()
    assert "anti_cheat" in failing, report.as_feedback()


def test_weakened_assertion_fails_sensitivity(tmp_path):
    """V3's anti-cheat gate only counts assertions; it does not judge their
    strength. `assert cache is not None` keeps the same assert count as
    the original (1), so V3 alone lets it through -- this is exactly why
    V2 (semantic, via the mutant) is the gate that actually catches this,
    not a redundant belt-and-suspenders check. Confirmed empirically: the
    first version of this test asserted anti_cheat would fail too, and it
    didn't -- see CHANGELOG.md.
    """
    candidate = _make_candidate(tmp_path, WEAKENED_FIX)
    report = verify_fix(CASE_DIR, candidate, TARGET_TEST, reruns=5)
    failing = {g.name for g in report.failing()}
    assert "sensitivity" in failing, report.as_feedback()
