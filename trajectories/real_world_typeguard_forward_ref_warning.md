# Trajectory: real_world_typeguard_forward_ref_warning

## Agent instructions (system prompt)

```
You are a careful software engineer fixing a flaky pytest test. You have full read/write access, but only within your working directory (a small, self-contained project copy). Do not read, write, or run commands against any path outside your working directory, even if it is technically reachable -- everything you need to diagnose and fix this is already inside it.

Investigate before you change anything:
- Read the failing test and the production code it exercises.
- Look for other test files that might interact with it (shared state, execution order, leaked globals, environment variables).
- Run the test suite with Bash (e.g. `python -m pytest tests/ -q`) to confirm your understanding of the failure and, once you've made a change, to confirm the fix actually works. Rerunning a few times is reasonable evidence; a single green run is not proof of anything for a flaky test.

Constraints:
- Keep the target test function's exact name unchanged. You may add new test functions if that improves coverage.
- Do not weaken or delete assertions, add sleeps/retries/skip markers, or otherwise make the symptom disappear without fixing the underlying cause.
- When you believe the fix is complete and you've verified it by running the suite, say so briefly and stop. Don't keep exploring past that point.
```

## Initial prompt

```
The test `tests/test_forward_ref_guessing.py::test_b_same_warning_again` in this project is flaky: it sometimes fails when rerun, even though nothing about the underlying code changes between runs.

Diagnose the root cause and fix it.
```

## Run

**Tool call** `Bash`: `{"command": "cd \"$(pwd)\" && ls && echo \"---\" && find . -name \"*.py\" -path \"*test*\" | head -50", "description": "List project files and test files"}`

**Tool call** `Bash`: `{"command": "pwd && ls -la", "description": "Show working directory"}`

**Tool result:**
```
conftest.py
src
tests
---
./conftest.py
./tests/test_forward_ref_guessing.py
```

**Tool result:**
```
/tmp/tmps7du393f/candidate
total 1
drwxr-xr-x 1 Alexandre 197121   0 Aug 28 20:36 .
drwxr-xr-x 1 Alexandre 197121   0 Aug 28 20:36 ..
-rw-r--r-- 1 Alexandre 197121 155 Aug 28 20:34 conftest.py
drwxr-xr-x 1 Alexandre 197121   0 Aug 28 20:35 src
drwxr-xr-x 1 Alexandre 197121   0 Aug 28 20:35 tests
```

**Tool call** `Read`: `{"file_path": "/tmp/tmps7du393f/candidate/conftest.py"}`

**Tool result:**
```
File does not exist. Note: your current working directory is C:\Users\user\AppData\Local\Temp\tmps7du393f\candidate.
```

**Tool call** `Read`: `{"file_path": "/tmp/tmps7du393f/candidate/tests/test_forward_ref_guessing.py"}`

**Tool result:**
```
File does not exist. Note: your current working directory is C:\Users\user\AppData\Local\Temp\tmps7du393f\candidate.
```

**Tool call** `Bash`: `{"command": "cd /tmp/tmps7du393f/candidate && find src -type f | head -100", "description": "List src files"}`

**Tool result:**
```
src/typechecker.py
src/__init__.py
src/__pycache__/typechecker.cpython-314.pyc
src/__pycache__/__init__.cpython-314.pyc
```

**Tool call** `Read`: `{"file_path": "C:\\Users\\user\\AppData\\Local\\Temp\\tmps7du393f\\candidate\\conftest.py"}`

**Tool result:**
```
1	"""Make this case's `src` package importable without installing it."""
2	import sys
3	from pathlib import Path
4	
5	sys.path.insert(0, str(Path(__file__).parent))
6
```

**Tool call** `Read`: `{"file_path": "C:\\Users\\user\\AppData\\Local\\Temp\\tmps7du393f\\candidate\\tests\\test_forward_ref_guessing.py"}`

**Tool result:**
```
1	"""Flaky for the same reason agronholm/typeguard's real
2	test_forward_ref_policy_guess was: Python's `warnings` module only emits
3	each unique (message, category, module, lineno) combination once per
4	process by default. Both tests below call check_annotation() from the
5	same call site with the same resulting message, so whichever test runs
6	SECOND finds the warning already "seen" and pytest.warns() reports
7	"DID NOT WARN" -- even though check_annotation() ran correctly.
8	"""
9	import collections
10	
11	import pytest
12	
13	from src.typechecker import TypeHintWarning, check_annotation
14	
15	
16	def unresolvable_annotation(x: "OrderedDict"):  # noqa: F821
17	    pass
18	
19	
20	def test_a_triggers_the_warning_first():
21	    with pytest.warns(TypeHintWarning):
22	        check_ann
... (truncated, 1419 chars total)
```

**Tool call** `Read`: `{"file_path": "C:\\Users\\user\\AppData\\Local\\Temp\\tmps7du393f\\candidate\\src\\typechecker.py"}`

**Tool result:**
```
1	"""A minimal, faithful extraction of the mechanism behind a real bug:
2	agronholm/typeguard#221 (https://github.com/agronholm/typeguard/issues/221).
3	
4	typeguard's real ForwardRefPolicy.GUESS feature does this: when a type
5	annotation is an unresolved forward reference (a string), guess the real
6	type from the argument actually passed and warn about the substitution.
7	This module reproduces that one behavior standalone, without pulling in
8	typeguard itself (whose exact API from 2021 no longer exists in current
9	releases).
10	"""
11	import warnings
12	
13	
14	class TypeHintWarning(UserWarning):
15	    pass
16	
17	
18	def check_annotation(func, arg_name, arg_value, forward_ref_name):
19	    """If `arg_name`'s annotation is the unresolved forward reference
20	    `forward_ref_name`, 
... (truncated, 1276 chars total)
```

**Tool call** `Bash`: `{"command": "cd /tmp/tmps7du393f/candidate && python -m pytest --version 2>&1; echo \"---plugins---\"; pip list 2>/dev/null | grep -i -E \"pytest|random|order|repeat\"; echo \"---\"; python --version", "description": "Check pytest version and plugins"}`

**Tool result:**
```
pytest 9.1.1
---plugins---
pytest                    9.1.1
pytest-randomly           4.1.0
---
Python 3.14.0
```

**Tool call** `Bash`: `{"command": "cd /tmp/tmps7du393f/candidate && for s in 1 2 3 4 5 6; do echo \"=== seed $s ===\"; python -m pytest tests/ -q -p randomly -p \"no:cacheprovider\" --randomly-seed=$s 2>&1 | tail -n 8; done", "description": "Run suite with several random seeds"}`

**Tool result:**
```
=== seed 1 ===
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT WARN. No warnings of type (<class 'src.typechecker.TypeHintWarning'>,) were emitted.
E        Emitted warnings: [].

C:\Users\user\Downloads\micro1-hackathon\case-studies\typeguard_forward_ref_warning\tests\test_forward_ref_guessing.py:21: Failed
=========================== short test summary info ===========================
FAILED tests/test_forward_ref_guessing.py::test_a_triggers_the_warning_first
1 failed, 1 passed in 0.17s
=== seed 2 ===
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT WARN. No warnings of type (<class 'src.typechecker.TypeHintWarning'>,) were emitted.
E        Emitted warnings: [].

C:\Users\user\Downloads\micro1-hackathon\case-studies\typeguard_forward_ref
... (truncated, 3138 chars total)
```

**Tool call** `Write`: `{"file_path": "C:\\Users\\user\\AppData\\Local\\Temp\\tmps7du393f\\candidate\\tests\\test_forward_ref_guessing.py", "content": "\"\"\"Regression tests for src.typechecker.check_annotation().\n\nHistorical flakiness note\n-------------------------\nThese tests used to share a single module-level function::\n\n    def unresolvable_annotation(x: \"OrderedDict\"): ...\n\nBoth tests called check_annotation() against that same object. But\ncheck_annotation() *mutates* the function it is given -- once it has\nguessed the real type it does::\n\n    func.__annotations__[arg_name] = guessed\n\nso the annotation stops being the unresolved string \"OrderedDict\" and\nbecomes the actual ``collections.OrderedDict`` type. Whichever test ran\nfirst therefore permanently rewrote the shared function, and whichever\nran second handed check_annotation() an already-resolved annotation,\nwhich means no warning was emitted and ``pytest.warns()`` failed with\n\"DID NOT WARN\". With pytest-randomly shuffling test order, the victim\nalternated between the two tests from run to run -- classic flakiness.\n\nThe fix is to give every test its own freshly-built function (via the\n``func`` fixture) so there is no shared mutable state to leak.\n\"\"\"\nimport collections\n\nimport pytest\n\nfrom src.typechecker import TypeHintWarning, check_annotation\n\n\ndef make_unresolvable_annotation():\n    \"\"\"Build a *new* function whose ``x`` parameter is annotated with the\n    unresolved forward reference ``\"OrderedDict\"``.\n\n    A fresh object per call is essential: check_annotation() rewrites\n    ``__annotations__`` in place, so reusing one function would let that\n    mutation leak between tests (which run in random order).\n    \"\"\"\n    def unresolvable_annotation(x: \"OrderedDict\"):  # noqa: F821\n        pass\n\n    return unresolvable_annotation\n\n\n@pytest.fixture\ndef func():\n    return make_unresolvable_annotation()\n\n\ndef test_a_triggers_the_warning_first(func):\n    assert func.__annotations__[\"x\"] == \"OrderedDict\"\n    with pytest.warns(TypeHintWarning):\n        check_annotation(func, \"x\", collections.OrderedDict(), \"OrderedDict\")\n    assert func.__annotations__[\"x\"] is collections.OrderedDict\n\n\ndef test_b_same_warning_again(func):\n    assert func.__annotations__[\"x\"] == \"OrderedDict\"\n    with pytest.warns(TypeHintWarning) as record:\n        check_annotation(func, \"x\", collections.OrderedDict(), \"OrderedDict\")\n    assert len(record) == 1\n    assert func.__annotations__[\"x\"] is collections.OrderedDict\n"}`

**Tool result:**
```
The file C:\Users\user\AppData\Local\Temp\tmps7du393f\candidate\tests\test_forward_ref_guessing.py has been updated successfully. (file state is current in your context — no need to Read it back)
```

**Tool call** `Bash`: `{"command": "cd /tmp/tmps7du393f/candidate && for s in 1 2 3 4 5 6 7 8 9 10; do python -m pytest tests/ -q --randomly-seed=$s 2>&1 | tail -n 1; done; echo \"=== fresh processes, default random seed ===\"; for i in 1 2 3 4 5 6; do python -m pytest tests/ -q 2>&1 | tail -n 1; done", "description": "Run suite across many seeds and repeated fresh runs"}`

**Tool result:**
```
2 passed in 0.10s
2 passed in 0.09s
2 passed in 0.09s
2 passed in 0.09s
2 passed in 0.10s
2 passed in 0.09s
2 passed in 0.09s
2 passed in 0.09s
2 passed in 0.10s
2 passed in 0.09s
=== fresh processes, default random seed ===
2 passed in 0.09s
2 passed in 0.09s
2 passed in 0.09s
2 passed in 0.09s
2 passed in 0.09s
2 passed in 0.10s
```

**Agent:** ## Root cause

The flakiness was **order-dependent shared mutable state**, not the warnings registry described in the old test docstring (that theory is a red herring — `pytest.warns()` installs `simplefilter("always")`, so the per-process "warn once" behavior never applies here).

`check_annotation()` mutates the function it inspects:

```python
func.__annotations__[arg_name] = guessed   # "OrderedDict" (str)  ->  collections.OrderedDict (type)
```

Both `test_a_triggers_the_warning_first` and `test_b_same_warning_again` called it against the **same module-level `unresolvable_annotation` function**. The first test to run permanently rewrote that function's annotation from the unresolved string to the real type. The second test then passed an already-resolved annotation, so `isinstance(annotation, str)` was `False`, no warning fired, and `pytest.warns()` failed with `DID NOT WARN`.

With `pytest-randomly` installed, the test order is reshuffled every run, so the victim alternated between `test_a` and `test_b` — hence "flaky on rerun".

## Fix

Removed the shared state: added a `make_unresolvable_annotation()` factory and a `func` fixture so each test gets its own fresh function with a pristine `"OrderedDict"` forward-ref annotation. No assertions were weakened (I also added a pre-condition assert that the annotation starts as the string). Test names are unchanged.

## Verification

`python -m pytest tests/ -q` across 10 different `--randomly-seed` values and 6 fresh default-seed runs: **2 passed** every time (previously 1 failed on every run, alternating which test).

*(turn 13, cost $0.1027 notional, stop_reason=end_turn)*

## Verification (closed the loop)

```
[PASS] stability: 0/30 fresh-process runs failed
[PASS] sensitivity: mutant correctly caught by the suite: 
..\..\tmps7du393f\candidate\tests\test_forward_ref_guessing.py:64: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_forward_ref_guessing.py::test_a_triggers_the_warning_first
FAILED tests/test_forward_ref_guessing.py::test_b_same_warning_again - Assert...
2 failed in 0.18s
[PASS] anti_cheat: no forbidden patterns; assert count held or increased
[PASS] blast_radius: 2/2 tests in the case passed
VERDICT: PASS
```
