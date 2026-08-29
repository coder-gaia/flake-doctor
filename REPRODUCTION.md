# Reproduction guide

Written for someone starting from a clean checkout of this repository, with no
other context than what's in this file.

## Prerequisites

- **Python 3.14** (developed and tested on 3.14.0; the stack is close to pure
  stdlib plus small pinned libraries, so 3.11+ likely works, but 3.14 is what
  was actually run).
- **One of two ways to authenticate the LLM calls** (baseline and agent runs
  only; detection and verification never call an LLM):
  - A paid **`ANTHROPIC_API_KEY`** from [console.anthropic.com](https://console.anthropic.com), set as an environment variable, billed per token, standard for most reproducers, **or**
  - The **Claude Code CLI** (`claude`) installed and logged into a Claude
    Pro/Max subscription. `claude_agent_sdk` resolves credentials in the same
    order the CLI itself does: `ANTHROPIC_API_KEY` first, a logged-in
    subscription session as fallback. **No code changes are needed either
    way**: this is why the project moved off the raw Anthropic SDK onto the
    Claude Agent SDK (see `CHANGELOG.md`).
- Git, to clone the repo.

No external data, accounts, or services beyond the above. Every benchmark
case is synthetic and self-contained, committed in `benchmark/cases/`.

## Setup

```bash
git clone <this-repo-url>
cd flake-doctor
pip install -r requirements.txt
```

Verify one of the two auth paths works:

```bash
# Path A: paid API key
export ANTHROPIC_API_KEY=sk-ant-...        # PowerShell: $env:ANTHROPIC_API_KEY = "sk-ant-..."

# Path B: Claude Pro/Max subscription
claude --version                            # should print a version, e.g. 2.1.247
```

## What each command does, and what to expect

### 1. Detection and verification (no LLM, no cost)

Measure a case's empirical flake rate directly:

```bash
python -m flakedoctor.detect benchmark/cases/timing_ttl_second_boundary "tests/test_ttl_cache.py::test_set_then_get_within_ttl" --reruns 40
```

Expected output: a fail count close to the rate recorded in that case's
`case.yaml` (e.g. `4/40 failed (10.0%)`), plus one sample failure traceback.
Runs in a few seconds.

Run this project's own harness tests (also no LLM cost):

```bash
python -m pytest tests/ -q
```

Expected: `8 passed` in under two minutes (mostly spent on `test_verify_harness.py`'s
real fresh-process reruns).

### 2. Baseline B1 (one direct prompt, no tools)

One case:

```bash
python -m baselines.single_prompt benchmark/cases/timing_ttl_second_boundary "tests/test_ttl_cache.py::test_set_then_get_within_ttl"
```

Full 14-case evaluation:

```bash
python -m flakedoctor.eval b1 --reruns 30
```

Expected: a per-case PASS/FAIL/ERROR line as each case finishes, then a
summary block, then `Saved: results/b1_baseline.json`. The canonical run in
this repo reached **9/14 (64.3%) Verified Repair Rate**; rerunning may shift
one or two cases (LLM output is not deterministic; see the "Design
correction: fixers must keep the target test's exact name" and the run-to-run
variance note in `CHANGELOG.md` for the actual range observed, 50%-64.3%
across three runs before that fix).

### 3. B2 (agent with tools, no verification loop)

One case, with the full tool-call trajectory printed:

```bash
python -m flakedoctor.agent benchmark/cases/order_dependence_cross_file "tests/test_billing.py::test_new_user_pays_full_price" --verbose
```

Full evaluation:

```bash
python -m flakedoctor.eval b2 --reruns 30
```

Canonical result: **13/14 (92.9%)**, zero sandbox violations. See
`results/b2_agent_no_verification.json` and the real fixed files each case
produced under `results/candidates/b2_agent_no_verification/`.

### 4. Final agent (verify-and-retry loop)

One case:

```bash
python -m flakedoctor.agent benchmark/cases/order_dependence_fixture_leak "tests/test_inventory.py::test_catalog_starts_empty_for_a_fresh_scenario" --verify --verbose
```

Full evaluation:

```bash
python -m flakedoctor.eval final --reruns 30
```

Canonical result: **13/14 (92.9%) in the batch; 14/14 real correct fixes**
once a transient, unreproduced infrastructure timeout on one case is counted
by its immediate clean retry instead of the timeout itself (full explanation
in `CHANGELOG.md`).

### 5. Trajectories (deliverable 4)

The two representative trajectories checked into `trajectories/` were
produced with:

```bash
python -m scripts.generate_trajectories b2      # trajectories/b2_order_dependence_cross_file.{md,jsonl}
python -m scripts.generate_trajectories final   # trajectories/final_order_dependence_fixture_leak.{md,jsonl}
```

Rerunning will produce different (but structurally similar) trajectories,
since the model's exact tool-call sequence is not deterministic; the `.md`
files are the easiest way to read one start to finish, the `.jsonl` files
are the mechanical trace.

### 6. Real-world validation case: a bug we did not design

[`case-studies/typeguard_forward_ref_warning/`](case-studies/typeguard_forward_ref_warning/)
is sourced from a real, documented issue,
[agronholm/typeguard#221](https://github.com/agronholm/typeguard/issues/221),
found via the [Illinois Dataset of Flaky Tests](https://github.com/TestingResearchIllinois/idoft).
It sits outside `benchmark/cases/` on purpose, so it can never be confused
with one of the 14 designed cases. Full provenance and the investigation
that led to the final version are in `case-studies/typeguard_forward_ref_warning/case.yaml`.

Prove the flake is real (no LLM call, a few seconds):

```bash
python -m flakedoctor.detect case-studies/typeguard_forward_ref_warning "tests/test_forward_ref_guessing.py::test_b_same_warning_again" --reruns 20
```

Expected: a fail count around 50-65%, ending in the same `DID NOT WARN`
error text the real GitHub issue reports.

Run the agent against it (1-2 min, notional cost like the single-case
commands above):

```bash
python -m flakedoctor.agent case-studies/typeguard_forward_ref_warning "tests/test_forward_ref_guessing.py::test_b_same_warning_again" --verify --verbose
```

Canonical result: **PASS on the first attempt**, all four gates green. The
saved trajectory (`trajectories/real_world_typeguard_forward_ref_warning.md`)
shows the agent explicitly rejecting an outdated theory left in the test
file's own docstring before proposing the real cause; the fixed files it
produced are kept at `case-studies/typeguard_forward_ref_warning/agent_fix/`.

## Approximate runtime and cost

Measured on the development machine (Windows, Python 3.14, Claude Pro
subscription auth, `claude-sonnet-5`):

| Step | Wall-clock (14 cases) | Notes |
|---|---|---|
| `flakedoctor.detect` / `pytest tests/` | seconds to ~2 min | no LLM call |
| B1 full eval | ~5-10 min | mean 60s/case |
| B2 full eval | ~30-40 min | mean 143s/case |
| Final full eval | ~35-70 min | mean 300s/case, median 175s; one case hit a rare 120s subprocess timeout (1695s total on that case alone), see `CHANGELOG.md` |

**Cost is not currently captured per case in the committed `results/*.json`
files**: a real gap, not a rounding choice, and it's disclosed here rather
than papered over. `flakedoctor/eval.py`'s `CaseResult` records wall-clock
seconds but not the notional `$` each fixer call reported, so the batch
files above can't be summed into an exact total. What exists instead are
real, individually-observed notional costs from documented single-case runs
and the two saved trajectories, all under a Claude Pro/Max subscription (so
these are the *list-price equivalent* Anthropic reports, not a bill; see
`CHANGELOG.md`'s Claude Agent SDK entry for what that distinction means and
why it's `$0` of actual spend on this subscription):

- B1 (no tools): **$0.01-0.02** per case.
- B2 / final agent (tools, one attempt): **$0.04-0.09** per case, higher for
  cases needing more investigation (the hard cross-file case cost $0.087-$0.095
  across two separate runs).
- Final agent, a case that needed a retry: **$0.13** total for both attempts
  (`trajectories/final_order_dependence_fixture_leak.jsonl`).

Reproducing with a paid `ANTHROPIC_API_KEY` instead of a subscription: expect
these same per-case figures to be actual, billed cost at `claude-sonnet-5`
list pricing, so roughly **$0.15-0.30** for a full B1 batch and
**$0.60-1.30** for a full B2 or final-agent batch. Budget a little above
that range if retries fire on more cases than they did here.
