"""A thin, local-only web UI over the same engine the CLI uses.

Nothing in flakedoctor/agent.py, flakedoctor/verify.py, or
flakedoctor/detect.py changed its behavior for this: this package adds an
HTTP layer (flakedoctor.web.app) that calls the exact same functions the
CLI calls, and a static page (flakedoctor/web/static/index.html) that
renders the same event stream --verbose already prints, live, in a
browser, with a case picker instead of typing a path and a test id.

Deliberately not a hosted, multi-user product: authentication is via
whatever Claude Code session is logged in on the machine running this
(a Claude Pro/Max subscription or ANTHROPIC_API_KEY, see REPRODUCTION.md),
the same as the CLI. Anyone who wants to use this runs it on their own
machine, under their own credentials -- see this package's README section
for how.
"""
