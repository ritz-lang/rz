"""Tests for ritz0_inproc, the suite's in-process ritz0 (AGAST #1805).

The suite used to launch ~600 `python3 ritz0.py` processes, each paying
~0.8 s to import the emitter and llvmlite before compiling a program that
takes milliseconds.  `run_ritz0` is a drop-in for that subprocess.run: it
forks a child of a forkserver that has already imported ritz0, runs ritz0's
real `main()` in it (so CLI defaults and --test mode are exactly the CLI's),
and returns a CompletedProcess.  `ritz0_oracle` builds on it: compile, link,
run, cached by sha256 of the source for the session.

These tests pin that the drop-in agrees with the real CLI, does not launch
ritz0 processes, isolates compiles from each other, and that the cache
neither misses on a repeat nor hits on a different program.
"""

import os
import subprocess
import sys

import pytest

import ritz0_inproc
from ritz0_inproc import RITZ0_PY, RITZ_ROOT, ritz0_oracle, run_ritz0

pytestmark = pytest.mark.integration

OK_PROGRAM = """\
const K: i32 = -7

pub fn main() -> i32
    return 0 - K
"""

# The oracle links one module, like the test_ritz1_* files it serves: no
# ritzlib import, output through ritz0's `write` syscall builtin.
PRINTING_PROGRAM = """\
pub fn main() -> i32
    write(1, c"hello oracle\\n", 13)
    5
"""

BAD_PROGRAM = """\
pub fn main() -> i32
    return undefined_name_1805
"""


def _env():
    return dict(os.environ, RITZ_PATH=str(RITZ_ROOT))


def _cli(args, cwd):
    return subprocess.run(
        [sys.executable, str(RITZ0_PY), *args],
        cwd=cwd, env=_env(), capture_output=True, text=True, timeout=300,
    )


def test_compile_matches_the_cli(tmp_path):
    """Same exit code and byte-identical IR as `python3 ritz0.py`."""
    src = tmp_path / "p.ritz"
    src.write_text(OK_PROGRAM)
    cli = _cli([str(src), "-o", str(tmp_path / "cli.ll")], tmp_path)
    inp = run_ritz0([str(src), "-o", str(tmp_path / "inp.ll")],
                    cwd=tmp_path, env=_env(), use_cache=False)
    assert cli.returncode == inp.returncode == 0, (cli.stderr, inp.stderr)
    assert (tmp_path / "cli.ll").read_text() == (tmp_path / "inp.ll").read_text()
    assert "Compiled" in inp.stdout


def test_failure_is_reported_like_the_cli(tmp_path):
    src = tmp_path / "bad.ritz"
    src.write_text(BAD_PROGRAM)
    cli = _cli([str(src), "-o", str(tmp_path / "cli.ll")], tmp_path)
    inp = run_ritz0([str(src), "-o", str(tmp_path / "inp.ll")],
                    cwd=tmp_path, env=_env(), use_cache=False)
    assert cli.returncode != 0
    assert inp.returncode == cli.returncode
    assert "undefined_name_1805" in inp.stdout + inp.stderr


def test_test_mode_runs(tmp_path):
    """`--test` (ritzunit) works through the drop-in too."""
    src = tmp_path / "t.ritz"
    src.write_text("[[test]]\nfn test_one() -> i32\n    assert 1 + 1 == 2\n    0\n")
    inp = run_ritz0([str(src), "--test"], cwd=tmp_path, env=_env())
    assert inp.returncode == 0, inp.stdout + inp.stderr
    assert "0 failed" in inp.stdout


def test_no_ritz0_process_is_launched(tmp_path):
    """The point of the helper: zero `ritz0.py` launches, by the CLI's own log."""
    log = tmp_path / "launches.log"
    src = tmp_path / "p.ritz"
    src.write_text(OK_PROGRAM)
    env = dict(_env(), RITZ_TEST_RITZ0_LOG=str(log))
    inp = run_ritz0([str(src), "-o", str(tmp_path / "p.ll")],
                    cwd=tmp_path, env=env, use_cache=False)
    assert inp.returncode == 0
    lines = log.read_text().splitlines()
    assert lines and all(line.startswith("inproc ") for line in lines), lines
    # Control: a real launch is logged untagged, so the count can tell them apart.
    cli_log = tmp_path / "cli.log"
    subprocess.run(
        [sys.executable, str(RITZ0_PY), str(src), "-o", str(tmp_path / "r.ll")],
        cwd=tmp_path, env=dict(_env(), RITZ_TEST_RITZ0_LOG=str(cli_log)),
        capture_output=True, timeout=300,
    )
    (line,) = cli_log.read_text().splitlines()
    assert not line.startswith("inproc ")


def test_compiles_are_isolated(tmp_path):
    """Each compile runs in a fresh fork: emitter state cannot leak across.

    A program that defines a struct `Leak1805` and one that does not mention
    it must each compile as if alone — a leaked definition would make the
    second program's IR carry the first's type.
    """
    a = tmp_path / "a.ritz"
    a.write_text(
        "struct Leak1805\n    x: i64\n\npub fn main() -> i32\n"
        "    var s: Leak1805 = Leak1805 { x: 4 }\n    s.x as i32\n"
    )
    b = tmp_path / "b.ritz"
    b.write_text(OK_PROGRAM)
    for s in (a, b):
        r = run_ritz0([str(s), "-o", str(s.with_suffix(".ll"))],
                      cwd=tmp_path, env=_env(), use_cache=False)
        assert r.returncode == 0, r.stderr
    assert "Leak1805" not in b.with_suffix(".ll").read_text()


def test_compile_cache_hits_on_identical_input(tmp_path):
    for d in ("one", "two"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "p.ritz").write_text(OK_PROGRAM + f"\n# {1805}\n")
    before = dict(ritz0_inproc.STATS)
    r1 = run_ritz0([str(tmp_path / "one/p.ritz"), "-o", str(tmp_path / "one/p.ll")],
                   cwd=tmp_path / "one", env=_env(), use_cache=True)
    r2 = run_ritz0([str(tmp_path / "two/p.ritz"), "-o", str(tmp_path / "two/p.ll")],
                   cwd=tmp_path / "two", env=_env(), use_cache=True)
    assert r1.returncode == r2.returncode == 0
    assert ritz0_inproc.STATS["cache_hits"] == before["cache_hits"] + 1
    assert ritz0_inproc.STATS["forks"] == before["forks"] + 1
    assert (tmp_path / "one/p.ll").read_text() == (tmp_path / "two/p.ll").read_text()
    # The replayed stdout names the second compile's paths, not the first's.
    assert "one/p.ritz" not in r2.stdout


def test_compile_cache_sees_imported_siblings(tmp_path):
    """A change to an imported sibling module is a different input."""
    main = "import helper\n\npub fn main() -> i32\n    helper_value()\n"
    outs = []
    for value in (3, 4):
        d = tmp_path / f"v{value}"
        d.mkdir()
        (d / "helper.ritz").write_text(f"pub fn helper_value() -> i32\n    {value}\n")
        (d / "main.ritz").write_text(main)
        r = run_ritz0([str(d / "main.ritz"), "-o", str(d / "main.ll")], cwd=d, env=_env(),
                      use_cache=True)
        assert r.returncode == 0, r.stdout + r.stderr
        outs.append((d / "main.ll").read_text())
    assert outs[0] != outs[1]


def test_compile_cache_is_off_by_default(tmp_path):
    """A hit would skip ritz0's side effects (sig files, "Skipped"), which
    tests of incremental compilation examine — so callers opt in."""
    src = tmp_path / "p.ritz"
    src.write_text(OK_PROGRAM + "\n# default-off-1805\n")
    before = dict(ritz0_inproc.STATS)
    for out in ("a.ll", "b.ll"):
        run_ritz0([str(src), "-o", str(tmp_path / out)], cwd=tmp_path, env=_env())
    assert ritz0_inproc.STATS["cache_hits"] == before["cache_hits"]
    assert ritz0_inproc.STATS["forks"] == before["forks"] + 2


def test_timeout_kills_the_compile(tmp_path, monkeypatch):
    src = tmp_path / "p.ritz"
    src.write_text(OK_PROGRAM)
    monkeypatch.setattr(ritz0_inproc, "_CHILD_DELAY_FOR_TESTS", 30.0)
    with pytest.raises(subprocess.TimeoutExpired):
        run_ritz0([str(src), "-o", str(tmp_path / "p.ll")],
                  cwd=tmp_path, env=_env(), timeout=1, use_cache=False)


def test_oracle_returns_exit_code_and_stdout():
    res = ritz0_oracle(PRINTING_PROGRAM)
    assert res.ir_ok
    assert res.rc == 5
    assert res.stdout == "hello oracle\n"


def test_oracle_reports_compile_failure():
    res = ritz0_oracle(BAD_PROGRAM)
    assert not res.ir_ok
    assert res.rc is None
    assert "undefined_name_1805" in res.diagnostics


def test_oracle_is_cached_by_source():
    before = dict(ritz0_inproc.STATS)
    first = ritz0_oracle(OK_PROGRAM + "\n# oracle-cache-1805\n")
    second = ritz0_oracle(OK_PROGRAM + "\n# oracle-cache-1805\n")
    assert first == second and first.rc == 7
    assert ritz0_inproc.STATS["oracle_hits"] == before["oracle_hits"] + 1
    other = ritz0_oracle(OK_PROGRAM.replace("-7", "-6"))
    assert other.rc == 6
