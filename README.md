# Flake Doctor

> An agent that diagnoses and repairs flaky pytest tests, and proves the repair is real before handing it to you.
>
> Built for the micro1 Agentic Workflows Hackathon (Aug 28–30, 2026). Everything in this repository was built during the hackathon window; nothing pre-existed it.

## Who has this problem

Any developer or maintainer on a team whose CI turns red for reasons unrelated to the commit that triggered it: timing assumptions, execution order, shared state, concurrency, or environment drift. Any test suite that exercises time, randomness, ordering, or shared resources eventually gets here.

## The bottleneck

Flaky tests hurt in three layers, and the third one is the one nobody automates:

1. **Reproducing is expensive.** A 4% flake needs dozens of runs to even show up. Nobody does that by hand.
2. **The root cause usually isn't in the test that failed.** Global state pollution, execution order, a shared fixture: the failing test is the victim, not the culprit.
3. **The standard "fix" hides the bug.** `time.sleep(2)`, `@pytest.mark.flaky(reruns=3)`, `@pytest.mark.skip`, a loosened assertion. CI turns green, the suite quietly rots, and whatever production bug that test used to catch is never caught again: the team loses the test *and* doesn't know it lost it.

The real cost isn't the time spent fixing a flake. It's the silent erosion of trust in the suite.

## Does the agent solve it well

Flake Doctor reproduces the flake under controlled conditions, diagnoses the root cause, and proposes a patch, then runs that patch through four deterministic gates it does not control: **stability** (0/30 reruns), **sensitivity via mutation testing** (a known bug in production code must still make the test fail), an **anti-cheat AST scan** (no sleep/rerun/skip/xfail tricks, no drop in assertion count), and **blast-radius** (the rest of the suite still passes). A failing gate feeds structured evidence back to the agent for another attempt, up to a retry budget of 2.

Measured on all 14 benchmark cases, the same cases and the same verifier for every fixer, applied after the fact so no fixer ever sees the mutant it will be judged against:

| Fixer | Verified Repair Rate | Cheat Rate | What changed |
|---|---|---|---|
| B1: one direct prompt, no tools | 9/14 (64.3%) | 3/14 (21.4%) | Baseline. Sees only the flaky test file. |
| B2: agent with tools, no verification | 13/14 (92.9%) | 1/14 (7.1%) | Same model, can read production source and run pytest itself. |
| **Final: agent + verify-and-retry loop** | **13/14 (92.9%) batch, 14/14 real fixes** | **0/14 (0%)** | Same agent; a failing gate sends structured feedback back for another attempt. |

**Cheat Rate** is the number that matters most: the fraction of fixes that look stable (0/30 reruns fail) but would let a real regression through uncaught. It is what a plain "tests pass now" check cannot see, and it is where verification earns its keep. 21.4% down to 0% is the actual size of the false-confidence problem this project set out to close, not the headline pass-rate jump.

The final agent's one non-pass in its batch was a transient 120-second subprocess timeout in the harness, not a wrong fix; an immediate identical retry passed cleanly. Full evidence for every number above, including three real engineering incidents this evaluation itself surfaced (a sandbox escape, a JUnit parsing bug, and this timeout), is in the [Improvement Changelog](CHANGELOG.md). Representative agent trajectories, including one where the retry loop actually fires and the agent hand-verifies its own second attempt with self-injected mutants, are in [`trajectories/`](trajectories/).

**Tested beyond the 14 designed cases, too.** [`case-studies/typeguard_forward_ref_warning/`](case-studies/typeguard_forward_ref_warning/) is a real, documented bug from [agronholm/typeguard#221](https://github.com/agronholm/typeguard/issues/221), a root cause outside the 7 categories the benchmark was built around. The agent fixed it on the first attempt and, in its own diagnosis, explicitly corrected an outdated theory still sitting in the test file's own docstring. Trajectory in [`trajectories/real_world_typeguard_forward_ref_warning.md`](trajectories/real_world_typeguard_forward_ref_warning.md).

## Can another person reproduce the result

Yes: see [REPRODUCTION.md](REPRODUCTION.md) for exact commands, expected output, versions, and approximate runtime and cost, written for a clean checkout with no other context.

## Using it without the terminal

The CLI (`python -m flakedoctor.agent ...`) is the primary interface, the same one every number above was measured with. For picking a case and watching a real run happen without typing paths, `python -m flakedoctor.web` starts a small local server at `http://127.0.0.1:8000`: pick a case, toggle the verify-and-retry loop on or off, click Run, and watch the same tool-call log and four-gate scorecard `--verbose` prints, live, in a browser.

It calls the exact same functions the CLI does, nothing is precomputed or replayed. It is deliberately not a hosted product: it authenticates with whatever Claude Code session is logged in on the machine running it (a Pro/Max subscription or `ANTHROPIC_API_KEY`, see REPRODUCTION.md), same as the CLI, so it only ever runs under the credentials and rate limit of whoever starts it, on their own machine. See [`flakedoctor/web/__init__.py`](flakedoctor/web/__init__.py) for why that boundary is deliberate, not a shortcut.

## Status

Core pipeline complete: benchmark, oracle, baseline, agent, verify-and-retry loop, and trajectory capture are all built, evaluated, and evidenced above. Remaining: the solution video and a final clean-environment reproduction pass.

## Repository layout

```
flakedoctor/
  detect.py      deterministic flake detection (fresh-subprocess reruns, no LLM)
  verify.py      the four verification gates (no LLM)
  agent.py       the tool-using fixer, with and without the verify-and-retry loop
  eval.py        runs a fixer across every benchmark case and verifies each result
  trajectory.py  renders a captured run into JSONL + a human-readable Markdown walkthrough
  web/           optional local web UI over the same functions the CLI calls
                 (python -m flakedoctor.web), not a hosted product
baselines/
  single_prompt.py  B1: one direct prompt, no tools, no execution
benchmark/cases/ 14 synthetic flaky-test cases used for evaluation, each with a
                 known mutant (see CHANGELOG.md for the full list and rationale)
case-studies/    real, externally-sourced bugs used to test generalization
                 beyond the designed benchmark (kept separate from it on purpose)
tests/           tests for this project's own harness (not the benchmark fixtures)
results/         evaluation output and real fixer-written artifacts; every claim
                 in this README and the changelog traces to a file here
trajectories/    representative agent trajectories (required deliverable)
```

## License

TBD.
