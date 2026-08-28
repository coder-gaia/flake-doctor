"""Flaky for the same reason agronholm/typeguard's real
test_forward_ref_policy_guess was: Python's `warnings` module only emits
each unique (message, category, module, lineno) combination once per
process by default. Both tests below call check_annotation() from the
same call site with the same resulting message, so whichever test runs
SECOND finds the warning already "seen" and pytest.warns() reports
"DID NOT WARN" -- even though check_annotation() ran correctly.
"""
import collections

import pytest

from src.typechecker import TypeHintWarning, check_annotation

# Shared module-level object, on purpose -- see case.yaml for why. The
# real typeguard test defines this function *inside* each test body (a
# fresh object every run), which isolates a different bug (Python's
# warnings registry) that no longer reproduces on current pytest. Sharing
# one function here reproduces a related real bug instead: check_annotation()
# mutates __annotations__ in place, so reusing the same function object
# lets that mutation leak across tests.
def unresolvable_annotation(x: "OrderedDict"):  # noqa: F821
    pass


def test_a_triggers_the_warning_first():
    with pytest.warns(TypeHintWarning):
        check_annotation(unresolvable_annotation, "x", collections.OrderedDict(), "OrderedDict")


def test_b_same_warning_again():
    # Bug in this test (and test_a): both assume check_annotation() will
    # see the unresolved "OrderedDict" annotation and warn. Whichever
    # test runs first permanently resolves it on the shared function
    # object, so whichever runs second gets an already-resolved
    # annotation and no warning at all.
    with pytest.warns(TypeHintWarning) as record:
        check_annotation(unresolvable_annotation, "x", collections.OrderedDict(), "OrderedDict")
    assert len(record) == 1
    assert unresolvable_annotation.__annotations__["x"] is collections.OrderedDict
