"""Every build subprocess runs under a wall-clock bound (AGAST #3632).

AGAST #1731 bounded the per-module `clang -c` after an unbounded one hung
every gate. The other children of build.py and `rz` (the compiler per
module, list_deps, the links, `as`, `ar`, the build.py children `rz` runs)
still had no timeout, so a wedged one hung its caller, and CI, until
something outside killed it. Each now runs under one of two bounds:

* STEP_TIMEOUT_ENV: one step of a package build (a module compile, an
  import scan, a link, `as`, `ar`, an IR verify, a runtime object).
* CHILD_TIMEOUT_ENV: a child that runs many steps: a `build.py build|test`
  that `rz` starts, a package's test.sh, ritz0's own test suite, cas.py.

Defaults are generous; a healthy step takes seconds. Both can be overridden
from the environment in seconds, as RITZ_CLANG_OBJ_TIMEOUT can. A program
the user runs (`build.py run`, `rz run`) is theirs: RUN_TIMEOUT_ENV bounds
it only when set.

Standard library only: `rz` imports this without loading the compiler.
"""

from __future__ import annotations

import os
import subprocess
import sys

STEP_TIMEOUT_ENV = "RITZ_STEP_TIMEOUT"
STEP_TIMEOUT_DEFAULT = 600
CHILD_TIMEOUT_ENV = "RITZ_CHILD_TIMEOUT"
CHILD_TIMEOUT_DEFAULT = 7200

# The exit status a timed-out run reports, as coreutils `timeout` does.
TIMED_OUT = 124


def env_seconds(name: str, default: int) -> int:
    """`name` from the environment as a positive int, else `default` (with a
    warning when it is set to something else)."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"  ⚠ ignoring {name}={raw!r} (not an integer); using {default}",
              file=sys.stderr)
        return default
    return value if value > 0 else default


def step_timeout() -> int:
    return env_seconds(STEP_TIMEOUT_ENV, STEP_TIMEOUT_DEFAULT)


def child_timeout() -> int:
    return env_seconds(CHILD_TIMEOUT_ENV, CHILD_TIMEOUT_DEFAULT)


def timeout_message(cmd, timeout: int, env_name: str) -> str:
    return (f"{os.path.basename(str(cmd[0]))} timed out after {timeout}s "
            f"({env_name}): {' '.join(str(c) for c in cmd)}")


def run(cmd, *, timeout: int, env_name: str, **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run under a `timeout`, which `env_name` sets.

    On timeout the child is killed and waited for; what it printed so far is
    kept, and the reason is appended to its captured stderr (to its stdout
    when stderr goes there, else printed). A grandchild still holding the
    pipe does not hold up the return: on POSIX, run() stops reading at the
    timeout. Returns TIMED_OUT then; never raises TimeoutExpired.

    subprocess.run itself, not a Popen of our own: tests that spy on it
    still see every compile and link.
    """
    try:
        return subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired as exc:
        out, err = exc.stdout, exc.stderr
    note = f"\n✗ {timeout_message(cmd, timeout, env_name)}\n"
    text = any(kwargs.get(k) for k in ("text", "universal_newlines", "encoding", "errors"))
    if text:   # TimeoutExpired carries bytes even in text mode
        out, err = (x.decode(errors="replace") if isinstance(x, bytes) else x
                    for x in (out, err))
    tail = note if text else note.encode()
    piped = kwargs.get("capture_output") or kwargs.get("stderr") == subprocess.PIPE
    if piped:
        err = (err or tail[:0]) + tail
    elif kwargs.get("stderr") == subprocess.STDOUT and kwargs.get("stdout") == subprocess.PIPE:
        out = (out or tail[:0]) + tail    # one stream
    else:
        print(note.strip("\n"), file=sys.stderr)
    return subprocess.CompletedProcess(cmd, TIMED_OUT, out, err)


def step(cmd, **kwargs) -> subprocess.CompletedProcess:
    """One step of a package build, under STEP_TIMEOUT_ENV."""
    return run(cmd, timeout=step_timeout(), env_name=STEP_TIMEOUT_ENV, **kwargs)


def child(cmd, **kwargs) -> subprocess.CompletedProcess:
    """A child that runs many steps (a build.py, test.sh), under CHILD_TIMEOUT_ENV."""
    return run(cmd, timeout=child_timeout(), env_name=CHILD_TIMEOUT_ENV, **kwargs)


# `build.py run` / `rz run` start the user's own program, which may be a
# server meant to run until stopped: bounded only when this is set.
RUN_TIMEOUT_ENV = "RITZ_RUN_TIMEOUT"


def user_program(cmd, **kwargs) -> subprocess.CompletedProcess:
    """The program a user asked to run: no bound unless RUN_TIMEOUT_ENV is set."""
    limit = env_seconds(RUN_TIMEOUT_ENV, 0)
    if not limit:
        return subprocess.run(cmd, timeout=None, **kwargs)
    return run(cmd, timeout=limit, env_name=RUN_TIMEOUT_ENV, **kwargs)
