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

Flake Doctor reproduces the flake under controlled conditions, diagnoses the root cause, and proposes a patch, then runs that patch through four deterministic gates it does not control: **stability** (0/50 reruns), **sensitivity via mutation testing** (a known bug in production code must still make the test fail), an **anti-cheat AST scan** (no sleep/rerun/skip/xfail tricks), and **blast-radius** (the rest of the suite still passes). A failing gate feeds structured evidence back to the agent for another attempt, up to a retry budget.

The full evaluation design (primary metric: Verified Repair Rate; the Cheat Rate metric that isolates what verification actually buys you; the baselines; and the benchmark cases) is summarized in the [Improvement Changelog](CHANGELOG.md) and gets reported here once results exist.

## Can another person reproduce the result

See [REPRODUCTION.md](REPRODUCTION.md) *(coming in a later phase: clean-environment setup, exact commands, expected output, cost and runtime)*.

## Status

🚧 In active development. This README, the [Improvement Changelog](CHANGELOG.md), and [REPRODUCTION.md](REPRODUCTION.md) are filled in as the project progresses; see the changelog for the real build story, evidence included.

## Repository layout

```
flakedoctor/     agent, tools, verification gates, CLI
baselines/       the plain-prompt baseline (B1)
benchmark/cases/ synthetic flaky-test cases used for evaluation
results/         evaluation output: every claim in this README traces to a file here
trajectories/    representative agent trajectories (required deliverable)
```

## License

TBD.
