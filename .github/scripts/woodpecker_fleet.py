#!/usr/bin/env python3
"""Can huburght's Woodpecker run the builder matrix? (AGAST #4846)

    woodpecker_fleet.py <server-url> <owner/repo>

main.yml's builder-fleet job runs this and appends its one line of output,
`hosted=true` or `hosted=false`, to $GITHUB_OUTPUT. builder-packages and
builder-matrix run on GitHub's hosted runners only when it says true
(Aaron, 2026-11-26: hosted minutes only when the fleet is down).

The fleet can run it when, all anonymously (the repo is public there):

- the server answers /api/healthz with a 2xx;
- the repo is activated: /api/repos/lookup/<owner>/<repo> finds it;
- no recent pipeline of the repo has sat `pending` for STUCK_SECONDS: one
  that has means no agent is taking work (the rz agent is down), though the
  server is up.

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

STUCK_SECONDS = 30 * 60
TIMEOUT = 10

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


def main(argv: list[str]) -> int:
    if len(argv) != 3 or "/" not in argv[2]:
        print("usage: woodpecker_fleet.py <server-url> <owner/repo>", file=sys.stderr)
        return 2
    hosted, why = decide(argv[1], argv[2])
    print(f"woodpecker_fleet: {'hosted run' if hosted else 'Woodpecker runs it'}: {why}",
          file=sys.stderr)
    print(f"hosted={'true' if hosted else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
