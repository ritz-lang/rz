#!/usr/bin/env python3
"""ritz1 builds in parallel, under an overridable cap -- AGAST #1802.

ritz1 used to build serially everywhere (`make -C ritz1 ritz1`, `make -C ritz1
bootstrap`), although the `.d` import dependencies from #1659 make `-j` safe.
A cold serial bootstrap measured 278 s against 101 s at `-j8`, with
byte-identical binaries.

The level is a CAP, read from RITZ1_JOBS, rather than a bare `-j` or `nproc`:
the WSL VM shared by the gate and the task rooms has ~15 GB, and a `-j8` cold
build adds ~3.4 GB at peak, so the operator has to be able to turn it down.

Every place that builds ritz1 for the gate must honour the same variable:
  * projects/ritz/Makefile  (`ritz1`, `ritz1-bootstrap`, `_matrix_ritz1_built`)
  * tools/run_regression_matrix.py --rebuild
  * scripts/regression.sh Stage 4   (covered by scripts/test-regression-stage4.sh)
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RITZ_ROOT = HERE.parent
MATRIX = HERE / "run_regression_matrix.py"


def _load_matrix():
    spec = importlib.util.spec_from_file_location("_matrix_jobs", MATRIX)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


matrix = _load_matrix()


def _dry_run(target: str, **env) -> str:
    """`make -n <target>` in projects/ritz; recursive $(MAKE) lines are echoed."""
    full_env = {k: v for k, v in os.environ.items() if k != "RITZ1_JOBS"}
    full_env.update(env)
    # MAKEFLAGS from an enclosing make would leak its own -j into the output.
    full_env.pop("MAKEFLAGS", None)
    full_env.pop("MFLAGS", None)
    r = subprocess.run(["make", "-n", target], cwd=RITZ_ROOT, env=full_env,
                       capture_output=True, text=True)
    return r.stdout + r.stderr


def _ritz1_make_lines(out: str) -> list[str]:
    return [line for line in out.splitlines()
            if re.search(r"\bmake\b.*-C ritz1\b", line)]


@pytest.mark.unit
@pytest.mark.parametrize("target", ["ritz1", "ritz1-bootstrap", "_matrix_ritz1_built"])
def test_makefile_builds_ritz1_with_the_jobs_cap(target):
    lines = _ritz1_make_lines(_dry_run(target, RITZ1_JOBS="3"))
    assert lines, f"`make -n {target}` shows no ritz1 sub-make"
    for line in lines:
        assert re.search(r"(^|\s)-j3(\s|$)", line), line


@pytest.mark.unit
def test_makefile_default_cap_is_at_most_8():
    lines = _ritz1_make_lines(_dry_run("ritz1"))
    assert lines
    m = re.search(r"(?:^|\s)-j(\d+)(?:\s|$)", lines[0])
    assert m, f"no numeric -j in {lines[0]!r} (an uncapped -j can OOM the VM)"
    assert 1 <= int(m.group(1)) <= min(8, os.cpu_count() or 1)


@pytest.mark.unit
def test_matrix_rebuild_jobs_reads_the_env_cap(monkeypatch):
    monkeypatch.setenv("RITZ1_JOBS", "2")
    assert matrix.ritz1_make_jobs() == 2


@pytest.mark.unit
def test_matrix_rebuild_jobs_default_is_capped(monkeypatch):
    monkeypatch.delenv("RITZ1_JOBS", raising=False)
    assert 1 <= matrix.ritz1_make_jobs() <= min(8, os.cpu_count() or 1)


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["", "0", "-4", "lots"])
def test_matrix_rebuild_jobs_ignores_nonsense(monkeypatch, bad):
    """A bad override falls back to the default rather than `-j0`/`-jlots`."""
    monkeypatch.setenv("RITZ1_JOBS", bad)
    assert 1 <= matrix.ritz1_make_jobs() <= min(8, os.cpu_count() or 1)


@pytest.mark.unit
def test_matrix_rebuild_passes_jobs_to_make(monkeypatch):
    calls = []

    class _R:
        returncode = 0

    def fake_run(argv, **kw):
        calls.append(argv)
        return _R()

    monkeypatch.setenv("RITZ1_JOBS", "5")
    monkeypatch.setattr(matrix.subprocess, "run", fake_run)
    assert matrix.rebuild_ritz1(env={}) == 0
    assert calls and calls[0][:1] == ["make"]
    assert "-j5" in calls[0] and "bootstrap" in calls[0], calls[0]
