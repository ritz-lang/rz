"""build.py names the failing [[test]] fn and its exit code (AGAST #4052).

A gate flake in valet's test_static_range printed only
"✗ test_static_range.ritz — 7 passed, 1 failed": the `Failures:` block that
`ritz0 --test` prints ("  - test_x: exited with code 2") was filtered out,
because build.py echoed only lines containing "FAIL" or "assertion". The
cause of the flake (a fixed /tmp path) had to be inferred, not read.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
RITZ0_DIR = PKG_DIR / "ritz0"
for d in (str(PKG_DIR), str(RITZ0_DIR)):
    if d not in sys.path:
        sys.path.insert(0, d)


@pytest.fixture
def test_runner():
    return importlib.import_module("test_runner")


@pytest.fixture
def buildpy(tmp_path):
    """A fresh build.py, so a monkeypatch cannot leak between tests."""
    spec = importlib.util.spec_from_file_location(
        f"ritz_buildpy_4052_{tmp_path.name}", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_a_failing_file_names_each_failed_fn_and_its_rc(tmp_path, monkeypatch,
                                                        buildpy, test_runner, capsys):
    t = tmp_path / "test_x.ritz"
    t.write_text("")
    failures = ["test_serve_in_file_range_sends_206: exited with code 2",
                "test_crashy: crashed with signal 11\n      boom on stderr"]
    monkeypatch.setattr(test_runner, "run_test_file",
                        lambda path, verbose=False, compiler="ritz0": (7, 2, failures))

    got = buildpy.run_test_file(t, tmp_path, buildpy.test_env_for_files(), 60)
    out = capsys.readouterr().out
    assert (got["status"], got["passed"], got["failed"]) == ("fail", 7, 2)
    assert "✗ test_x.ritz — 7 passed, 2 failed" in out
    assert "wall " in out and "binary " in out
    assert "test_serve_in_file_range_sends_206: exited with code 2" in out
    assert "test_crashy: crashed with signal 11" in out
    assert "boom on stderr" in out  # the failed fn's own output, too


@pytest.mark.unit
def test_failure_lines_reads_only_the_failures_block(buildpy):
    stdout = ("noise mentioning nothing\n\n7 passed, 1 failed\n\nFailures:\n"
              "  - test_a: exited with code 3\n      line one\n")
    assert buildpy.failure_lines(stdout) == [
        "- test_a: exited with code 3", "    line one"]
    assert buildpy.failure_lines("3 passed, 0 failed\n") == []
