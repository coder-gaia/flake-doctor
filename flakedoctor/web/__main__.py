"""python -m flakedoctor.web -- starts the local web UI on 127.0.0.1:8000.

Bound to localhost, not 0.0.0.0: this runs real Bash/pytest against a
temp copy of a project and authenticates an LLM call using whatever is
logged in on this machine (see flakedoctor/web/__init__.py). It has no
business being reachable from the network.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("flakedoctor.web.app:app", host="127.0.0.1", port=8000, reload=False)
