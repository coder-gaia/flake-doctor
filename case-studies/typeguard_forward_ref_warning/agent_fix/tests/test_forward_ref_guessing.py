"""Regression tests for src.typechecker.check_annotation().

Historical flakiness note
-------------------------
These tests used to share a single module-level function::

    def unresolvable_annotation(x: "OrderedDict"): ...

Both tests called check_annotation() against that same object. But
check_annotation() *mutates* the function it is given -- once it has
guessed the real type it does::

    func.__annotations__[arg_name] = guessed

so the annotation stops being the unresolved string "OrderedDict" and
becomes the actual ``collections.OrderedDict`` type. Whichever test ran
first therefore permanently rewrote the shared function, and whichever
ran second handed check_annotation() an already-resolved annotation,
which means no warning was emitted and ``pytest.warns()`` failed with
"DID NOT WARN". With pytest-randomly shuffling test order, the victim
alternated between the two tests from run to run -- classic flakiness.

The fix is to give every test its own freshly-built function (via the
``func`` fixture) so there is no shared mutable state to leak.
"""
import collections

import pytest

from src.typechecker import TypeHintWarning, check_annotation


def make_unresolvable_annotation():
    """Build a *new* function whose ``x`` parameter is annotated with the
    unresolved forward reference ``"OrderedDict"``.

    A fresh object per call is essential: check_annotation() rewrites
    ``__annotations__`` in place, so reusing one function would let that
    mutation leak between tests (which run in random order).
    """
    def unresolvable_annotation(x: "OrderedDict"):  # noqa: F821
        pass

    return unresolvable_annotation


@pytest.fixture
def func():
    return make_unresolvable_annotation()


def test_a_triggers_the_warning_first(func):
    assert func.__annotations__["x"] == "OrderedDict"
    with pytest.warns(TypeHintWarning):
        check_annotation(func, "x", collections.OrderedDict(), "OrderedDict")
    assert func.__annotations__["x"] is collections.OrderedDict


def test_b_same_warning_again(func):
    assert func.__annotations__["x"] == "OrderedDict"
    with pytest.warns(TypeHintWarning) as record:
        check_annotation(func, "x", collections.OrderedDict(), "OrderedDict")
    assert len(record) == 1
    assert func.__annotations__["x"] is collections.OrderedDict
