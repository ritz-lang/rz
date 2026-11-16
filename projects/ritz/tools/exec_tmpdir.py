#!/usr/bin/env python3
"""A temp dir the gate and smoke can run binaries from (AGAST #3704).

The matrix harness, the ritz0 pytest suite and several scripts build
executables under the temp dir and run them.  On a host whose /tmp is mounted
`noexec` (bangerang: a JumpCloud CIS policy re-applies it every 50 minutes)
every one of those runs fails with `PermissionError: [Errno 13]`, which reads
as a broken commit.  It is the host's doing, so:

  * run-gate.sh gives every gate its own TMPDIR next to its checkout and
    proves it exec-able with `exec_tmpdir.py probe <dir>` before the first
    step; a dir that fails the probe is a SETUP ERROR, not a test failure.
  * smoke.py and run_regression_matrix.py call ensure_exec_tmpdir(): when the
    ambient TMPDIR (or /tmp) can't run a file, they switch TMPDIR -- for
    themselves and every child -- to FALLBACK, under the user's cache dir.

One probe, used by both: write a two-line shell script, chmod +x it, run it.

Usage:
    exec_tmpdir.py probe DIR   exit 0 if a file in DIR can be run, else print
                               "SETUP ERROR: ..." naming DIR and exit 3
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

# "This machine can't do it", not "this commit is broken": smoke.EXIT_SETUP.
EXIT_SETUP = 3

PROBE_SCRIPT = "#!/bin/sh\nexit 0\n"

# exec_fn(path) runs the probe file and returns its exit code, or raises
# OSError (EACCES on a noexec mount).  Injectable so tests need no mount.
ExecFn = Callable[[str], int]


def _exec(path: str) -> int:
    return subprocess.run([path], check=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=30).returncode


def default_fallback() -> Path:
    cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache) / "ritz" / "exec-tmp"


def probe(directory: str | os.PathLike, exec_fn: ExecFn = _exec) -> str | None:
    """None if a file written to `directory` can be made executable and run;
    otherwise the reason it can't."""
    d = str(directory)
    try:
        fd, path = tempfile.mkstemp(prefix="exec_probe_", suffix=".sh", dir=d)
    except OSError as e:
        return f"cannot create a file in {d}: {e}"
    try:
        with os.fdopen(fd, "w") as f:
            f.write(PROBE_SCRIPT)
        os.chmod(path, 0o700)
        rc = exec_fn(path)
        if rc != 0:
            return f"a probe script in {d} exited {rc}, not 0"
        return None
    except (OSError, subprocess.SubprocessError) as e:
        return f"cannot run a file in {d} (noexec mount?): {e}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


class SetupError(RuntimeError):
    """Neither the ambient temp dir nor the fallback can run a file."""


def ensure_exec_tmpdir(fallback: Path | None = None, exec_fn: ExecFn = _exec,
                       environ: dict | None = None,
                       out: TextIO = sys.stderr) -> Path | None:
    """Make sure tempfile (and every child, via TMPDIR) uses an exec-able dir.

    Returns None when the ambient temp dir already works (nothing changed),
    else the fallback dir it switched TMPDIR to.  Raises SetupError, naming
    both dirs, when the fallback fails the probe too.
    """
    env = os.environ if environ is None else environ
    ambient = tempfile.gettempdir()
    why = probe(ambient, exec_fn)
    if why is None:
        return None
    fb = Path(fallback) if fallback is not None else default_fallback()
    try:
        fb.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise SetupError(f"temp dir {ambient} can't run binaries ({why}), "
                         f"and the fallback {fb} can't be created: {e}") from e
    why_fb = probe(fb, exec_fn)
    if why_fb is not None:
        raise SetupError(f"temp dir {ambient} can't run binaries ({why}), "
                         f"and neither can the fallback: {why_fb}")
    env["TMPDIR"] = str(fb)
    # gettempdir() caches its answer; make the next call see the new TMPDIR.
    tempfile.tempdir = None
    print(f"# TMPDIR {ambient} can't run binaries ({why}); using {fb}", file=out, flush=True)
    return fb


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "probe":
        print("usage: exec_tmpdir.py probe DIR", file=sys.stderr)
        return 2
    why = probe(argv[1])
    if why is None:
        return 0
    print(f"SETUP ERROR: TMPDIR {argv[1]} can't run binaries: {why}")
    return EXIT_SETUP


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
