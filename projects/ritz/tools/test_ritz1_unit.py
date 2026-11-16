"""tools/ritz1_unit.py: ritz1's unit-suite gate (AGAST #1556).

ritz1/test/ held 23 .ritz files with no [[test]] fn, which nothing built or
ran.  The gate that replaces them must go red when it finds nothing to run,
and must be a step the gate actually executes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ritz1_unit

RITZ = ritz1_unit.RITZ_ROOT
REPO = RITZ.parent.parent

PASS = {"status": "pass", "passed": 3, "failed": 0}


def fake(outcomes: dict):
    """A run_file stand-in answering by file name; records its calls."""
    calls = []

    def run(tfile, scratch):
        calls.append(tfile.name)
        return outcomes[tfile.name]

    run.calls = calls
    return run


def test_zero_files_fails(tmp_path, capsys):
    run = fake({})
    assert ritz1_unit.main(["--dir", str(tmp_path)], run=run) == 1
    assert run.calls == []
    assert "found 0 test files" in capsys.readouterr().out


def test_one_file_not_passing_fails_the_run(tmp_path, capsys):
    for n in ("test_a.ritz", "test_b.ritz"):
        (tmp_path / n).write_text("")
    run = fake(
        {
            "test_a.ritz": PASS,
            "test_b.ritz": {"status": "empty", "passed": 0, "failed": 0},
        }
    )
    assert ritz1_unit.main(["--dir", str(tmp_path)], run=run) == 1
    assert sorted(run.calls) == ["test_a.ritz", "test_b.ritz"]
    assert "1 of 2 files did not pass: test_b.ritz" in capsys.readouterr().out


def test_all_passing_passes(tmp_path, capsys):
    (tmp_path / "test_a.ritz").write_text("")
    assert (
        ritz1_unit.main(["--dir", str(tmp_path)], run=fake({"test_a.ritz": PASS})) == 0
    )
    assert "1 files, 3 tests passed" in capsys.readouterr().out


def test_unwritten_outcome_is_an_error_not_a_pass(tmp_path, monkeypatch):
    """build.py dying before it writes --unit-result must not read as a pass."""

    class Done:
        stdout = stderr = ""

    monkeypatch.setattr(ritz1_unit.subprocess, "run", lambda *a, **k: Done())
    out = ritz1_unit.run_file(tmp_path / "test_x.ritz", tmp_path)
    assert out["status"] == "error"


def test_a_file_with_no_test_fn_fails_end_to_end(tmp_path):
    """Real build.py: a file with no [[test]] fn is a failure, not 0 passed."""
    (tmp_path / "test_empty.ritz").write_text("fn main() -> i32\n  0\n")
    assert ritz1_unit.main(["--dir", str(tmp_path)]) == 1


def test_suite_on_disk_is_only_test_files():
    """Everything in ritz1/test/ is a [[test]] file the gate runs.  A
    program or fixture dropped there would fail the gate as `empty`; this
    names the problem first, and keeps subdirectories out (not globbed)."""
    entries = sorted(p.name for p in ritz1_unit.TEST_DIR.iterdir())
    assert entries, "ritz1/test/ is empty"
    for name in entries:
        p = ritz1_unit.TEST_DIR / name
        assert p.is_file() and name.startswith("test_") and name.endswith(".ritz"), name
        assert "[[test]]" in p.read_text().splitlines(), f"{name}: no [[test]] fn"


def test_bootstrap_job_runs_the_gate():
    """The step exists in CI's bootstrap job (what ci-local and the room
    gate run), and its make target exists."""
    wf = yaml.safe_load((REPO / ".github/workflows/main.yml").read_text())
    steps = wf["jobs"]["bootstrap"]["steps"]
    runs = [(s.get("run", ""), s.get("working-directory")) for s in steps]
    assert ("make ritz1-unit", "projects/ritz") in runs
    makefile = (RITZ / "Makefile").read_text()
    assert "\nritz1-unit:" in makefile
    assert "tools/ritz1_unit.py" in makefile
