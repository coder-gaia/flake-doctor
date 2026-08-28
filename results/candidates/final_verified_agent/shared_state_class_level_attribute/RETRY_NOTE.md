# Note on this candidate

The original 14-case batch run (`results/final_verified_agent.json`) records this
case as `ERROR`: one of `flakedoctor.detect`'s pytest subprocess calls hit its
120-second timeout after 1694s of total wall time. That run's candidate directory
was cleaned up before anyone could inspect it (a gap `flakedoctor/eval.py` no
longer has, see CHANGELOG.md).

The files in this directory are from an immediate, identical retry
(`run_verified_agent_on_case`, same case, same target test, same `verify_reruns`),
run separately and persisted here manually. That retry passed cleanly on the
first attempt, well under a minute, all four gates green, cost $0.0375. The
timeout did not reproduce.

`results/final_verified_agent.json` is left as the original batch produced it
(one honest ERROR, not silently rewritten to PASS). This directory is the
follow-up evidence referenced in CHANGELOG.md's "Final agent (verify-and-retry)
established" entry, not a second row in that JSON.
