"""ritzlib/tests under ritz1 and ritz1_selfhosted, in CI (AGAST #3805).

Nothing ran `rz test ritz/ritzlib/tests --compiler ritz1`: the only ritz1 run
was the regression matrix, and two whole files (test_strview.ritz,
test_slice_syntax.ritz) rotted under ritz1 unnoticed until #3766.  The
`ritzlib-tests-ritz1` make target runs the suite under both ritz1 compilers,
and main.yml's bootstrap job runs it, so ci-local (every room gate and train)
runs it too.  These tests pin both halves.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ci_local

RITZ = Path(__file__).resolve().parent.parent
TARGET = "ritzlib-tests-ritz1"


def _bootstrap_runs() -> list[str]:
    return [s.run.strip() for s in ci_local.load_steps() if s.job == "bootstrap"]


def test_bootstrap_job_runs_the_target_after_both_compilers_are_built():
    # A gate that is in no workflow is the bug this ticket exists for; the
    # bootstrap job is what ci-local runs.  It must come after the step that
    # builds ritz1 + ritz1_selfhosted, or it pays a cold serial build.
    steps = [s for s in ci_local.load_steps() if s.job == "bootstrap"]
    runs = [s.run.strip() for s in steps]
    assert f"make {TARGET}" in runs
    step = steps[runs.index(f"make {TARGET}")]
    assert step.workdir == "projects/ritz"
    assert runs.index("make ritz1-bootstrap") < runs.index(f"make {TARGET}")


def test_target_runs_ritzlib_tests_under_both_ritz1_compilers():
    # A dry run shows what the target would execute: one `rz test` of
    # ritz/ritzlib/tests per compiler, and never ritz0's default (the train's
    # package step already covers ritz0, #3909).
    out = subprocess.run(
        ["make", "-n", "--no-print-directory", TARGET],
        cwd=RITZ, capture_output=True, text=True, check=True,
    ).stdout
    tests = [ln for ln in out.splitlines() if "rz test ritz/ritzlib/tests" in ln]
    compilers = sorted(ln.split("--compiler", 1)[1].split()[0] for ln in tests
                       if "--compiler" in ln)
    assert compilers == ["ritz1", "ritz1_selfhosted"], out
    assert len(tests) == 2, out


def test_target_builds_both_compilers_first():
    # Run alone (or after a clean), the target must not fail for want of a
    # binary; in CI the prerequisite is a no-op after "Build ritz1 + ...".
    makefile = (RITZ / "Makefile").read_text()
    line = next(ln for ln in makefile.splitlines() if ln.startswith(f"{TARGET}:"))
    assert "ritz1-bootstrap" in line.split(":", 1)[1]
    assert f".PHONY: {TARGET}" in makefile
