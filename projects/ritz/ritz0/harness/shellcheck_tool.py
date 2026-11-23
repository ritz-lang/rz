"""The pinned shellcheck, for tests that lint shell scripts (AGAST #4360).

shellcheck used to be whatever the machine had: CI's ubuntu runner shipped
0.11 and the gate hosts shipped none, so every shellcheck test skipped on the
gate and a shell finding failed CI only (#4359, #4264).  shellcheck-py, a
wheel that carries the static shellcheck binary, is now pinned in
requirements-dev.txt and requirements.lock.  CI and every gate venv install it
from the same line, and the venv's bin dir comes before /usr/bin on PATH in
both, so they run the same shellcheck.

`shellcheck()` returns that binary's path, or fails the calling test when it
is missing or is not the version the lock pins.  It never skips: a missing
shellcheck is a venv that predates the pin, and the message says how to fix
it.  tools/test_shellcheck_tool.py fails any test that looks shellcheck up
with `shutil.which` itself.

`shellcheck()` spawns `shellcheck --version` once per process, so a test that
calls it must be marked `integration` (spawn_guard enforces that).
"""

from __future__ import annotations

import functools
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
LOCK = RITZ_ROOT / "requirements.lock"

INSTALL = (
    "python -m pip install -r projects/ritz/requirements.txt "
    "-r projects/ritz/requirements-dev.txt -c projects/ritz/requirements.lock"
)


def expected_version() -> str:
    """The shellcheck version requirements.lock pins.

    shellcheck-py's version is shellcheck's version plus one component for
    the wrapper's own release: 0.11.0.1 carries shellcheck 0.11.0.
    """
    m = re.search(r"^shellcheck-py==(\S+)", LOCK.read_text(), re.M)
    if not m:
        pytest.fail(f"{LOCK} does not pin shellcheck-py")
    return ".".join(m.group(1).split(".")[:3])


def parse_version(out: str) -> str | None:
    """The `version:` line of `shellcheck --version`."""
    m = re.search(r"^version:\s*(\S+)", out, re.M)
    return m.group(1) if m else None


def check_version(path: str, out: str) -> None:
    """Fail unless `out` (from `path --version`) is the pinned version."""
    want = expected_version()
    got = parse_version(out)
    if got != want:
        pytest.fail(
            f"{path} is shellcheck {got}, requirements.lock pins {want}; "
            f"a venv that is not first on PATH, or one that predates the pin. "
            f"Run in the gate's venv: {INSTALL}"
        )


@functools.cache
def _version_output(path: str) -> str:
    r = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
    return r.stdout


def shellcheck() -> str:
    """Path of the pinned shellcheck; fails the test if it is not on PATH."""
    path = shutil.which("shellcheck")
    if path is None:
        pytest.fail(
            "shellcheck is not on PATH. It is pinned (shellcheck-py in "
            "requirements-dev.txt and requirements.lock, AGAST #4360), so the "
            f"venv predates the pin. Run in the gate's venv: {INSTALL}"
        )
    check_version(path, _version_output(path))
    return path
