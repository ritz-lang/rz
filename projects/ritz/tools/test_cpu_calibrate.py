"""The gate host's CPU calibration (AGAST #3897).

cost_meter's CPU-seconds aren't the same on every host: at ef9a7e2b the same
suite measured 1,454.5 CPU-s on toffee and 2,347 on omegalisk.  So
tools/cpu_calibrate.py times a small fixed workload at the start of the
ritz0 step, and check_test_budget.py divides the suite's CPU-s by the host's
factor: that workload's CPU-s here over its CPU-s on the reference host
(`[calibration] reference_cpu_s` in test_budget.toml).

These tests run in `make tools-unit`.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import cpu_calibrate as cal  # noqa: E402
import exec_tmpdir  # noqa: E402


# --- how many copies run at once -----------------------------------------------
#
# The suite runs under `-n auto --maxprocesses "${PYTEST_J:-8}"`, and a core shared by two
# busy hyperthreads spends more CPU-s on the same work.  The workload runs as
# many copies at once as the suite has workers, so it pays the same contention.


@pytest.mark.unit
def test_jobs_follow_xdist_auto_capped_at_maxprocesses(monkeypatch):
    monkeypatch.delenv("PYTEST_J", raising=False)
    monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "3")
    assert cal.default_jobs() == 3
    monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "20")
    assert cal.default_jobs() == cal.MAX_PROCESSES == 8


@pytest.mark.unit
def test_jobs_cap_follows_the_gates_pytest_j(monkeypatch):
    """AGAST #4971: a gate with RZ_GATE_JOBS runs the suite at
    `--maxprocesses "${PYTEST_J:-8}"`, so the copies are capped there too."""
    monkeypatch.setenv("PYTEST_J", "24")
    monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "30")
    assert cal.default_jobs() == 24
    monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "20")
    assert cal.default_jobs() == 20
    for unusable in ("", "0", "many"):  # main.yml's `${PYTEST_J:-8}` reads "" as 8
        monkeypatch.setenv("PYTEST_J", unusable)
        monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "30")
        assert cal.default_jobs() == cal.MAX_PROCESSES == 8


@pytest.mark.unit
def test_jobs_without_the_override_use_the_cpu_count(monkeypatch):
    monkeypatch.delenv("PYTEST_J", raising=False)
    monkeypatch.delenv("PYTEST_XDIST_AUTO_NUM_WORKERS", raising=False)
    n = cal.default_jobs()
    assert 1 <= n <= cal.MAX_PROCESSES
    assert n <= (os.cpu_count() or 1)


# --- the workload ----------------------------------------------------------------


@pytest.mark.unit
def test_workload_is_fixed_and_independent_of_the_tree():
    """A workload made of ritz0 compiles would slow down with ritz0, and a
    2x slower compiler would leave the normalised suite figure where it was:
    the budget would stop seeing exactly what it exists to see.  So the
    workload uses nothing from the tree; only the host (CPU, kernel, Python,
    clang) moves it."""
    src = (TOOLS / "cpu_calibrate.py").read_text()
    for name in ("ritz0", "ritzlib", "build.py", "RITZ_PATH"):
        assert name not in src.split('"""', 2)[2], name
    assert isinstance(cal.PY_WORKLOAD, str)
    assert "define" in cal.reference_ir() and cal.reference_ir() == cal.reference_ir()


@pytest.mark.integration
def test_measure_counts_the_childrens_cpu_and_is_quick(tmp_path):
    t0 = time.monotonic()
    r = cal.measure(jobs=2, rounds=1, scratch=tmp_path)
    wall = time.monotonic() - t0
    # Every part of the workload runs in a child: the parent's own CPU is
    # bookkeeping.  A measurement that missed the children would read ~0.
    assert r["cpu_s"] > 0.2, r
    assert r["jobs"] == 2 and r["rounds"] == 1
    assert len(r["samples"]) == 1
    assert wall < 30, f"calibration took {wall:.1f} s wall; it must stay a few seconds"
    # Scratch is cleaned up: the gate runs this twice per gate.
    assert list(tmp_path.iterdir()) == []


@pytest.mark.integration
def test_cli_writes_the_report(tmp_path):
    out = tmp_path / "cal.json"
    r = subprocess.run([sys.executable, str(TOOLS / "cpu_calibrate.py"),
                        "--out", str(out), "--jobs", "1", "--rounds", "1"],
                       capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(out.read_text())
    assert d["cpu_s"] > 0 and d["jobs"] == 1
    assert "cpu calibration:" in r.stdout and f"{d['cpu_s']:.3f}" in r.stdout


@pytest.mark.unit
def test_median_of_rounds_ignores_one_outlier():
    assert cal.summarise([1.0, 1.1, 9.0]) == pytest.approx(1.1)
    assert cal.summarise([2.0]) == 2.0


# --- a host's fixed factor (AGAST #4172) -------------------------------------------
#
# A few seconds of workload just before a ~20-minute suite read 1.054 on skronk
# (normally ~1.67) when the box was busy, and failed two gates whose tests all
# passed.  A host can pin its factor (host.env's RZ_CPU_FACTOR, measured once
# on an idle box with --runs); the gate then passes --factor and nothing is
# timed.


@pytest.mark.unit
def test_fixed_factor_is_written_without_measuring(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("a fixed factor must not run the workload")
    monkeypatch.setattr(cal, "measure", boom)
    out = tmp_path / "cal.json"
    assert cal.main(["--out", str(out), "--factor", "1.67"]) == 0
    assert json.loads(out.read_text()) == {"factor": 1.67, "fixed": True}
    assert "fixed factor 1.670" in capsys.readouterr().out


@pytest.mark.unit
def test_fixed_factor_must_be_a_finite_number_above_zero(tmp_path):
    for bad in ("0", "-1.5", "nan", "inf", "fast"):
        with pytest.raises(SystemExit):
            cal.main(["--out", str(tmp_path / "cal.json"), "--factor", bad])
    assert not (tmp_path / "cal.json").exists()


@pytest.mark.unit
def test_runs_prints_each_factor_and_the_median_for_host_env(tmp_path, monkeypatch, capsys):
    """`--runs N` is how a host measures its RZ_CPU_FACTOR once, idle: N full
    calibrations, each over the budget's reference, and their median."""
    seq = iter([3.0, 9.0, 3.4])  # reference 2.0: factors 1.5, 4.5, 1.7
    monkeypatch.setattr(cal, "measure",
                        lambda jobs, rounds, scratch=None: {"cpu_s": next(seq)})
    # main resolves the scratch once, with a real exec probe; keep this a unit.
    monkeypatch.setattr(cal, "resolve_scratch", lambda scratch=None, **kw: tmp_path)
    b = tmp_path / "budget.toml"
    b.write_text("[calibration]\nreference_cpu_s = 2.0\n")
    assert cal.main(["--runs", "3", "--jobs", "1", "--budget", str(b)]) == 0
    out = capsys.readouterr().out
    assert "1.500" in out and "4.500" in out and "1.700" in out
    assert "RZ_CPU_FACTOR=1.700" in out.splitlines()[-1]


# --- an exec-capable scratch dir (AGAST #4431) --------------------------------------
#
# tempfile.mkdtemp(dir=None) puts the copies under $TMPDIR (/tmp), and on a
# host where that mount is noexec the linked binary exits 126 "Permission
# denied" (#4431 measured this on bangerang).  So the default probes the
# candidates -- --scratch, $TMPDIR, exec_tmpdir's cache fallback -- and uses
# the first that can run a file.  The probe is injected, so these tests need
# no noexec mount; the one below that does, skips without one.


def _fake_probe(cannot: set[str], seen: list[str] | None = None):
    """An exec probe under which only directories in `cannot` fail."""
    def probe(directory):
        p = str(directory)
        if seen is not None:
            seen.append(p)
        return f"{p} is noexec" if p in cannot else None
    return probe


@pytest.fixture
def scratch_env(monkeypatch, tmp_path):
    """$TMPDIR and the cache dir under tmp_path: deterministic candidate paths."""
    monkeypatch.setattr(tempfile, "tempdir", None)
    sysdir = tmp_path / "sys"
    sysdir.mkdir()
    monkeypatch.setenv("TMPDIR", str(sysdir))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return sysdir, tmp_path / "home" / ".cache" / "ritz" / "exec-tmp"


@pytest.mark.unit
def test_scratch_candidates_are_scratch_then_tmpdir_then_cache(scratch_env, tmp_path):
    sysdir, fallback = scratch_env
    explicit = tmp_path / "explicit"
    assert cal.scratch_candidates(explicit) == [explicit, sysdir, fallback]
    assert cal.scratch_candidates(None) == [sysdir, fallback]


@pytest.mark.unit
def test_resolve_uses_scratch_when_it_can_exec(scratch_env, tmp_path):
    explicit = tmp_path / "explicit"
    assert cal.resolve_scratch(explicit, probe_fn=_fake_probe(set()),
                               out=io.StringIO()) == explicit


@pytest.mark.unit
def test_resolve_skips_a_noexec_scratch_and_says_so(scratch_env, tmp_path):
    """A --scratch that can't exec does not stop the run: $TMPDIR is next."""
    sysdir, _fallback = scratch_env
    explicit = tmp_path / "explicit"
    seen: list[str] = []
    out = io.StringIO()
    got = cal.resolve_scratch(explicit, probe_fn=_fake_probe({str(explicit)}, seen), out=out)
    assert got == sysdir
    assert seen == [str(explicit), str(sysdir)]
    note = out.getvalue()
    assert str(explicit) in note and str(sysdir) in note and "noexec" in note


@pytest.mark.unit
def test_resolve_falls_back_from_a_noexec_tmpdir(scratch_env):
    """The ticket's case, with no --scratch: $TMPDIR is the noexec one."""
    sysdir, fallback = scratch_env
    got = cal.resolve_scratch(None, probe_fn=_fake_probe({str(sysdir)}), out=io.StringIO())
    assert got == fallback


@pytest.mark.unit
def test_resolve_creates_a_missing_candidate_dir(scratch_env, tmp_path):
    d = tmp_path / "nested" / "scratch"
    assert cal.resolve_scratch(d, probe_fn=lambda _: None, out=io.StringIO()) == d
    assert d.is_dir()


@pytest.mark.unit
def test_resolve_raises_setup_error_when_nothing_can_exec(scratch_env):
    sysdir, fallback = scratch_env
    with pytest.raises(exec_tmpdir.SetupError) as ei:
        cal.resolve_scratch(None, probe_fn=_fake_probe({str(sysdir), str(fallback)}),
                            out=io.StringIO())
    assert str(sysdir) in str(ei.value) and str(fallback) in str(ei.value)


@pytest.mark.unit
def test_the_docstring_documents_the_noexec_caveat():
    """The tool is run by hand for --runs; the caveat belongs where a reader
    looks first, not only in an error message."""
    doc = (TOOLS / "cpu_calibrate.py").read_text().split('"""', 2)[1]
    assert "noexec" in doc
    assert "--scratch" in doc


def _writable_noexec_mount() -> Path | None:
    """A dir on a rw,noexec mount this process can write to, else None.

    bangerang's /tmp; a GitHub runner's noexec mounts are /sys and /proc,
    which it cannot write.  A real mount, not a stub: this test's whole point
    is that exec really fails there.
    """
    try:
        lines = Path("/proc/mounts").read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        parts = line.split()
        if len(parts) < 4 or "noexec" not in parts[3].split(",") \
                or "rw" not in parts[3].split(","):
            continue
        for cand in (Path(parts[1]) / str(os.getuid()), Path(parts[1])):
            try:
                with tempfile.TemporaryDirectory(prefix="noexec_find_", dir=cand):
                    return cand
            except OSError:
                continue
    return None


@pytest.mark.integration
def test_measure_falls_back_when_the_ambient_temp_dir_cannot_exec(monkeypatch, tmp_path):
    """#4431 end to end: tempfile's default dir is a noexec mount, and
    measure() still runs the linked binary -- from the cache fallback."""
    bad = _writable_noexec_mount()
    if bad is None:
        pytest.skip("no writable noexec mount on this host (the stub-based "
                    "resolve tests cover the logic)")
    monkeypatch.setattr(tempfile, "tempdir", str(bad))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    r = cal.measure(jobs=1, rounds=1)
    assert r["cpu_s"] > 0.2, r
    assert (tmp_path / "cache" / "ritz" / "exec-tmp").is_dir()
