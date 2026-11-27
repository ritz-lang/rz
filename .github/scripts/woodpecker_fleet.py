#!/usr/bin/env python3
"""Can huburght's Woodpecker run the builder matrix? (AGAST #4846)

    woodpecker_fleet.py <server-url> <owner/repo>
    woodpecker_fleet.py --watch <commit> <server-url> <owner/repo>

The probe: main.yml's builder-fleet job runs it and appends its one line of
output, `hosted=true` or `hosted=false`, to $GITHUB_OUTPUT (Aaron,
2026-11-26: hosted minutes only when the fleet is down).

The watch (--watch): when the probe said Woodpecker, main.yml's
builder-watch job runs it to see Woodpecker actually start <commit>'s
pipeline. The server can be up with no agent taking the repo's work (the
first live push, 97eacd11d: pipeline #1 sat pending, and the probe, which
only knew stuck pipelines, had routed it to Woodpecker; no matrix ran
anywhere). It prints `hosted=` and `why=` lines; builder-packages and
builder-matrix run on GitHub only when hosted=true, and say why.

The fleet can run it when, all anonymously (the repo is public there):

- the server answers /api/healthz with a 2xx;
- the repo is activated: /api/repos/lookup/<owner>/<repo> finds it;
- no recent pipeline of the repo has sat `pending` for STUCK_SECONDS: one
  that has means no agent is taking work (the rz agent is down), though the
  server is up. STUCK_SECONDS is FALLBACK_SECONDS: a pipeline pending that
  long is one the watch gave up on.

The watch says Woodpecker runs it once a pipeline of <commit> has started
(`started` set, or `running`). It falls back to hosted when the pipeline is
still pending FALLBACK_SECONDS after it was created (or after the watch began,
if earlier, or if no pipeline of the commit shows up), or at once when one
finished without starting (killed while pending, a config error). API errors
in between are ridden out until the deadline. Anonymous, like the probe.

The watch can't cancel the pipelines it gave up on (that needs a token), so
.woodpecker/builder.yml's steps (woodpecker_builder_step.sh) skip themselves
when their pipeline started more than FALLBACK_SECONDS + SLACK_SECONDS after
it was created: GitHub ran that commit, and a queue of dead pipelines
doesn't cost the agent 15 minutes each when it appears. The slack makes an
edge case run twice, never zero times.

Any doubt (a timeout, an error, a body that doesn't parse) is a hosted run:
a matrix run twice costs minutes, a matrix not run at all hides a red
package. The script never fails the job; a usage error exits 2.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable

#: Woodpecker's time to start a commit's pipeline before GitHub runs the
#: matrix itself (rz, 2026-11-27: "N ~ 10, one constant").
#: woodpecker_builder_step.sh repeats it (test_woodpecker_builder.py pins it).
FALLBACK_SECONDS = 10 * 60
STUCK_SECONDS = FALLBACK_SECONDS
POLL_SECONDS = 20
TIMEOUT = 10
#: Pipeline statuses that end a pipeline; with `started` unset, it never ran.
FINISHED = frozenset({"success", "failure", "error", "killed", "declined", "skipped"})

Fetch = Callable[[str], tuple[int, bytes]]


def fetch(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def decide(server: str, repo: str, get: Fetch = fetch,
           now: float | None = None) -> tuple[bool, str]:
    """(hosted, why): hosted is True when GitHub should run the matrix."""
    now = time.time() if now is None else now
    server = server.rstrip("/")
    try:
        status, _ = get(f"{server}/api/healthz")
    except Exception as e:  # noqa: BLE001 -- any failure means "not up"
        return True, f"server unreachable: {e}"
    if not 200 <= status < 300:
        return True, f"server unhealthy: /api/healthz answered {status}"
    try:
        status, body = get(f"{server}/api/repos/lookup/{repo}")
        if status != 200:
            return True, f"repo {repo} not found on the server ({status}): not activated or not public"
        repo_id = int(json.loads(body)["id"])
    except Exception as e:  # noqa: BLE001
        return True, f"repo {repo} lookup failed: {e}"
    try:
        status, body = get(f"{server}/api/repos/{repo_id}/pipelines")
        if status != 200:
            return True, f"pipelines of {repo} answered {status}"
        pipelines = json.loads(body)
        stuck = [p for p in pipelines
                 if p.get("status") == "pending"
                 and now - float(p.get("created", now)) > STUCK_SECONDS]
    except Exception as e:  # noqa: BLE001
        return True, f"pipelines of {repo} unreadable: {e}"
    if stuck:
        return True, (f"{len(stuck)} pipeline(s) of {repo} pending over "
                      f"{STUCK_SECONDS // 60} min: no agent is taking work")
    return False, f"{server} is up and taking {repo}'s pipelines"


def watch(server: str, repo: str, commit: str, get: Fetch = fetch,
          clock: Callable[[], float] = time.time,
          sleep: Callable[[float], None] = time.sleep) -> tuple[bool, str]:
    """(hosted, why): hosted is True when Woodpecker didn't start <commit>."""
    server = server.rstrip("/")
    short = commit[:12]
    deadline = clock() + FALLBACK_SECONDS
    repo_id: int | None = None
    seen: dict | None = None
    last_error = ""
    while True:
        try:
            if repo_id is None:
                status, body = get(f"{server}/api/repos/lookup/{repo}")
                if status != 200:
                    raise OSError(f"repo lookup answered {status}")
                repo_id = int(json.loads(body)["id"])
            status, body = get(f"{server}/api/repos/{repo_id}/pipelines")
            if status != 200:
                raise OSError(f"pipelines answered {status}")
            mine = [p for p in json.loads(body) if p.get("commit") == commit]
            last_error = ""
        except Exception as e:  # noqa: BLE001 -- transient until the deadline
            last_error = str(e)
            mine = []
        for p in mine:
            seen = p
            if float(p.get("started") or 0) > 0 or p.get("status") == "running":
                return False, (f"Woodpecker pipeline #{p.get('number')} of {short} "
                               f"started ({p.get('status')})")
        for p in mine:
            if p.get("status") in FINISHED:
                return True, (f"Woodpecker pipeline #{p.get('number')} of {short} "
                              f"ended {p.get('status')} without starting")
            created = float(p.get("created") or 0)
            if created > 0:
                deadline = min(deadline, created + FALLBACK_SECONDS)
        now = clock()
        if now >= deadline:
            minutes = FALLBACK_SECONDS // 60
            if seen is not None:
                return True, (f"Woodpecker pipeline #{seen.get('number')} of {short} "
                              f"still {seen.get('status')} after {minutes} min: "
                              f"no agent is taking {repo}'s work")
            if last_error:
                return True, (f"Woodpecker unreadable for {minutes} min "
                              f"(last error: {last_error})")
            return True, (f"no pipeline of {short} on {server} after {minutes} min: "
                          f"did the Gitea push webhook fire?")
        sleep(max(1.0, min(POLL_SECONDS, deadline - now)))


def main(argv: list[str]) -> int:
    if len(argv) == 5 and argv[1] == "--watch":
        commit, server, repo = argv[2], argv[3], argv[4]
        if (len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit)
                or "/" not in repo):
            print("usage: woodpecker_fleet.py --watch <commit> <server-url> <owner/repo>",
                  file=sys.stderr)
            return 2
        hosted, why = watch(server, repo, commit)
        if hosted:
            # An annotation on the run's summary page, not just in the log.
            print(f"::warning title=Builder matrix falls back to GitHub::{why}",
                  file=sys.stderr)
        else:
            print(f"woodpecker_fleet: Woodpecker runs it: {why}", file=sys.stderr)
        print(f"hosted={'true' if hosted else 'false'}")
        print(f"why={why}")
        return 0
    if len(argv) != 3 or "/" not in argv[2]:
        print("usage: woodpecker_fleet.py [--watch <commit>] <server-url> <owner/repo>",
              file=sys.stderr)
        return 2
    hosted, why = decide(argv[1], argv[2])
    print(f"woodpecker_fleet: {'hosted run' if hosted else 'Woodpecker runs it'}: {why}",
          file=sys.stderr)
    print(f"hosted={'true' if hosted else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
