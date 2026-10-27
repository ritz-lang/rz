"""Tests for the `rz build/test --all -j N` worker pool (AGAST #1809).

`rz` schedules (project, test file) units on one bounded pool. What must hold:

  - concurrency never exceeds -j / rz.toml [build] max_jobs;
  - output is buffered per unit and printed in the serial order, whatever
    order the units finish in;
  - per-project verdicts, and therefore the known_failing / strict-xpass
    gate, are the serial sweep's: same failed set, same Σ line;
  - discovery stays in build.py (rz never globs test files).

The unit tests fake `rz.run_unit` so they need no compiler. One integration
test runs a real temp package through both paths and compares verdict lines.
"""

import importlib.machinery
import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

import pytest

RZ_PATH = Path(__file__).resolve().parents[3] / "rz"
PKG_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rz():
    spec = importlib.util.spec_from_loader(
        "rz_cli_parallel",
        importlib.machinery.SourceFileLoader("rz_cli_parallel", str(RZ_PATH)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def buildpy(request):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location(
        "ritz_buildpy_parallel", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# -j / rz.toml resolution
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestResolveJobs:
    def test_cli_flag_wins_over_config(self, rz):
        assert rz.resolve_jobs(3, {"build": {"max_jobs": 8}}) == 3

    def test_max_jobs_from_config(self, rz):
        assert rz.resolve_jobs(None, {"build": {"max_jobs": 5}}) == 5

    def test_parallel_false_means_serial(self, rz):
        cfg = {"build": {"parallel": False, "max_jobs": 8}}
        assert rz.resolve_jobs(None, cfg) == 1

    def test_cli_flag_beats_parallel_false(self, rz):
        cfg = {"build": {"parallel": False}}
        assert rz.resolve_jobs(4, cfg) == 4

    def test_default_is_cpu_count(self, rz, monkeypatch):
        monkeypatch.setattr(rz.os, "cpu_count", lambda: 6)
        assert rz.resolve_jobs(None, {}) == 6

    @pytest.mark.parametrize("bad", [0, -1, "8", True, 2.5])
    def test_bad_max_jobs_is_an_error(self, rz, bad):
        with pytest.raises(SystemExit):
            rz.resolve_jobs(None, {"build": {"max_jobs": bad}})

    def test_bad_cli_jobs_is_an_error(self, rz):
        with pytest.raises(SystemExit):
            rz.resolve_jobs(0, {})

    def test_workspace_rz_toml_is_read(self, rz):
        # The real rz.toml's max_jobs is what a bare `rz test --all` uses —
        # it was read by nothing before #1809.
        cfg = rz.load_workspace_config()
        expected = cfg["build"]["max_jobs"] if cfg["build"].get(
            "parallel", True) else 1
        assert rz.resolve_jobs(None, cfg) == expected

    @pytest.mark.parametrize("cmd", ["build", "test"])
    def test_j_flag_parses(self, rz, cmd):
        args = rz.build_parser().parse_args([cmd, "--all", "-j", "4"])
        assert args.jobs == 4
        args = rz.build_parser().parse_args([cmd, "--all"])
        assert args.jobs is None


# --------------------------------------------------------------------------
# The pool itself
# --------------------------------------------------------------------------

def _unit(rz, project, order, kind="build"):
    return rz.Unit(project=project, order=order, sched=order, kind=kind,
                   cmd=["true"], env={})


@pytest.mark.unit
class TestRunPool:
    def test_concurrency_bounded_by_jobs_and_reaches_it(self, rz, monkeypatch):
        lock = threading.Lock()
        live = [0]
        peak = [0]

        def fake_run(unit):
            with lock:
                live[0] += 1
                peak[0] = max(peak[0], live[0])
            time.sleep(0.05)
            with lock:
                live[0] -= 1
            unit.rc, unit.output = 0, ""
            return unit

        monkeypatch.setattr(rz, "run_unit", fake_run)
        units = [_unit(rz, f"p{i}", (i,)) for i in range(12)]
        done = []
        rz.run_pool(3, units, lambda u: done.append(u) or [])
        assert peak[0] == 3
        assert len(done) == 12

    def test_lowest_sched_runs_first_including_follow_ups(self, rz,
                                                         monkeypatch):
        # The pool hands out work by priority, not submission order: a
        # follow-up with a lower `sched` (a plan's files) overtakes queued
        # units. Submitting everything to the executor up front would run
        # A, B, C, X.
        order = []

        def fake_run(unit):
            order.append(unit.project)
            unit.rc, unit.output = 0, ""
            return unit

        monkeypatch.setattr(rz, "run_unit", fake_run)
        units = [_unit(rz, "A", (0,)), _unit(rz, "B", (2,)),
                 _unit(rz, "C", (3,))]
        rz.run_pool(1, units, lambda u: [_unit(rz, "X", (1,))]
                    if u.project == "A" else [])
        assert order == ["A", "X", "B", "C"]

    def test_follow_up_units_are_run(self, rz, monkeypatch):
        def fake_run(unit):
            unit.rc, unit.output = 0, unit.project
            return unit

        monkeypatch.setattr(rz, "run_unit", fake_run)
        seen = []

        def on_done(u):
            seen.append(u.project)
            if u.project == "root":
                return [_unit(rz, f"child{i}", (1, i)) for i in range(4)]
            return []

        rz.run_pool(2, [_unit(rz, "root", (0,))], on_done)
        assert sorted(seen) == ["child0", "child1", "child2", "child3", "root"]

    def test_unit_captures_stdout_and_stderr_in_order(self, rz):
        u = rz.Unit(project="x", order=(0,), sched=(0,), kind="build",
                    cmd=[sys.executable, "-c",
                         "import sys; print('out', flush=True); "
                         "print('err', file=sys.stderr, flush=True); "
                         "sys.exit(3)"],
                    env=None)
        rz.run_unit(u)
        assert u.rc == 3
        assert u.output.splitlines() == ["out", "err"]


# --------------------------------------------------------------------------
# The test sweep: deterministic output, serial verdicts
# --------------------------------------------------------------------------

class FakeWorkspace:
    """Fakes build.py's units. `spec[project]` gives the plan and per-file
    statuses; `delay` makes earlier units finish LATER, so any order that
    leaks through from completion order shows up in the output."""

    def __init__(self, spec):
        self.spec = spec
        self.ran = []
        self.lock = threading.Lock()

    def __call__(self, unit):
        with self.lock:
            self.ran.append((unit.project, unit.kind,
                             Path(unit.file).name if unit.file else None))
        p = self.spec[unit.project]
        # Reverse-order completion: project 0's units are slowest.
        time.sleep(0.02 * (len(self.spec) - unit.order[0]))
        if unit.kind == "plan":
            # A failed build still LISTS its files here (build.py writes
            # none): rz itself must not schedule anything after a failed
            # plan, whatever the plan file says.
            plan = {"built": p.get("built", True),
                    "no_harness": p.get("no_harness", False),
                    "files": [f"/pkg/{unit.project}/test/{f}"
                              for f in p.get("files", {})]
                    if not p.get("no_harness") else [],
                    "test_sh": p.get("test_sh", False)}
            unit.path.write_text(json.dumps(plan))
            unit.rc = 0 if plan["built"] and not plan["no_harness"] else 1
            unit.output = f"[plan {unit.project}]\n"
        elif unit.kind == "file":
            name = Path(unit.file).name
            status = p["files"][name]
            unit.path.write_text(json.dumps(
                {"status": status, "passed": 2 if status == "pass" else 1,
                 "failed": 1 if status == "fail" else 0}))
            unit.rc = 0 if status == "pass" else 1
            unit.output = f"    [{status} {name}]\n"
        else:  # test-sh
            unit.rc = 0 if p.get("test_sh_ok", True) else 1
            unit.output = "  [test.sh]\n"
        return unit


SPEC = {
    "alpha": {"files": {"a1.ritz": "pass", "a2.ritz": "fail",
                        "a3.ritz": "pass"}},
    "beta": {"built": False, "files": {"b1.ritz": "pass"}, "test_sh": True},
    "gamma": {"files": {"g1.ritz": "pass", "g2.ritz": "pass"},
              "test_sh": True},
    "delta": {},
    "eps": {"no_harness": True, "files": {"e1.ritz": "pass"},
            "test_sh": True},
}


@pytest.fixture
def fake(rz, monkeypatch):
    fw = FakeWorkspace(SPEC)
    monkeypatch.setattr(rz, "run_unit", fw)
    return fw


@pytest.mark.unit
class TestTestSweep:
    def test_failed_set_matches_serial_semantics(self, rz, fake, capsys):
        failed = rz.test_projects_parallel(list(SPEC), 4, "ritz0")
        # alpha: a failing file. beta: build failed. eps: no harness.
        # gamma (files + test.sh pass) and delta (no tests) pass.
        assert failed == ["alpha", "beta", "eps"]

    def test_failed_build_schedules_nothing_else(self, rz, fake, capsys):
        rz.test_projects_parallel(list(SPEC), 4, "ritz0")
        assert [k for p, k, _ in fake.ran if p == "beta"] == ["plan"]

    def test_no_harness_still_runs_test_sh(self, rz, fake, capsys):
        # Serial run_tests runs test.sh after the no-harness failure.
        rz.test_projects_parallel(list(SPEC), 4, "ritz0")
        assert sorted(k for p, k, _ in fake.ran if p == "eps") == [
            "plan", "test-sh"]

    def test_every_file_is_its_own_unit(self, rz, fake, capsys):
        rz.test_projects_parallel(list(SPEC), 4, "ritz0")
        files = sorted(f for p, k, f in fake.ran if k == "file")
        assert files == ["a1.ritz", "a2.ritz", "a3.ritz", "g1.ritz",
                         "g2.ritz"]

    def test_output_is_in_serial_order_despite_completion_order(
            self, rz, fake, capsys):
        rz.test_projects_parallel(list(SPEC), 8, "ritz0")
        out = capsys.readouterr().out
        banners = [l.split()[1] for l in out.splitlines()
                   if l.startswith("Testing: ")]
        assert banners == list(SPEC)
        alpha = out[out.index("Testing: alpha"):out.index("Testing: beta")]
        assert alpha.index("[pass a1.ritz]") < alpha.index(
            "[fail a2.ritz]") < alpha.index("[pass a3.ritz]")
        gamma = out[out.index("Testing: gamma"):out.index("Testing: delta")]
        # Serial order: plan, files, Σ, then test.sh.
        assert gamma.index("[plan gamma]") < gamma.index(
            "[pass g2.ritz]") < gamma.index("Σ") < gamma.index("[test.sh]")

    def test_output_identical_across_job_counts(self, rz, fake, capsys):
        rz.test_projects_parallel(list(SPEC), 1, "ritz0")
        one = capsys.readouterr().out
        rz.test_projects_parallel(list(SPEC), 8, "ritz0")
        eight = capsys.readouterr().out
        strip = lambda s: [l for l in s.splitlines()  # noqa: E731
                           if not l.startswith("rz: ")]
        assert strip(one) == strip(eight)

    def test_sigma_line_is_build_py_format(self, rz, fake, buildpy, capsys):
        rz.test_projects_parallel(["alpha"], 4, "ritz0")
        out = capsys.readouterr().out
        expected = buildpy.summarize_file_outcomes([
            {"status": "pass", "passed": 2, "failed": 0},
            {"status": "fail", "passed": 1, "failed": 1},
            {"status": "pass", "passed": 2, "failed": 0},
        ])
        assert expected in out.splitlines()

    def test_project_verdict_lines(self, rz, fake, capsys):
        rz.test_projects_parallel(list(SPEC), 4, "ritz0")
        out = capsys.readouterr().out
        assert "✗ alpha: tests failed (exit 1)" in out
        assert "✗ beta: tests failed (exit 1)" in out
        assert "gamma: tests failed" not in out
        delta = out[out.index("Testing: delta"):out.index("Testing: eps")]
        assert "⚠ No tests found, skipping" in delta

    def test_missing_result_json_is_a_failure(self, rz, monkeypatch, capsys):
        # A build.py unit that dies before writing its result must fail the
        # project, not vanish from the Σ line.
        def crash(unit):
            if unit.kind == "plan":
                unit.path.write_text(json.dumps(
                    {"built": True, "no_harness": False,
                     "files": ["/x/test/t.ritz"], "test_sh": False}))
                unit.rc = 0
            else:
                unit.rc = 1
            unit.output = ""
            return unit

        monkeypatch.setattr(rz, "run_unit", crash)
        assert rz.test_projects_parallel(["solo"], 2, "ritz0") == ["solo"]
        assert "1 compile-failed" in capsys.readouterr().out

    def test_unit_commands_target_build_py_units(self, rz, monkeypatch):
        cmds = []

        def record(unit):
            cmds.append(unit.cmd)
            if unit.kind == "plan":
                unit.path.write_text(json.dumps(
                    {"built": True, "no_harness": False,
                     "files": ["/x/test/t.ritz"], "test_sh": True}))
            else:
                if unit.kind == "file":
                    unit.path.write_text(json.dumps(
                        {"status": "pass", "passed": 1, "failed": 0}))
            unit.rc, unit.output = 0, ""
            return unit

        monkeypatch.setattr(rz, "run_unit", record)
        rz.test_projects_parallel(["solo"], 2, "ritz1")
        flat = [" ".join(c) for c in cmds]
        assert any("--unit-plan" in c and "--compiler ritz1" in c
                   for c in flat)
        assert any("--unit-file /x/test/t.ritz" in c and "--unit-result" in c
                   for c in flat)
        assert any("--unit-test-sh" in c for c in flat)
        assert all(str(rz.RITZ_BUILD) in c for c in flat)


@pytest.mark.unit
class TestGateWiring:
    """-j changes scheduling only; the gate sees the same arguments."""

    def _run(self, rz, monkeypatch, argv, failed):
        calls = {}
        monkeypatch.setattr(rz, "discover_projects", lambda: ["p", "q"])
        monkeypatch.setattr(rz, "test_projects_parallel",
                            lambda projects, jobs, compiler:
                            calls.setdefault("par", (projects, jobs)) and
                            list(failed))
        monkeypatch.setattr(rz, "build_projects_parallel",
                            lambda projects, jobs, extra:
                            calls.setdefault("bpar", (projects, jobs)) and
                            list(failed))
        monkeypatch.setattr(rz, "known_failing_from_config",
                            lambda kind: calls.setdefault("kf", kind) and
                            {"q": "AGAST #1 — x"})

        def gate(kind, f, kf, ran, list_kind=None):
            calls["gate"] = (kind, f, kf, ran, list_kind)
            return 0
        monkeypatch.setattr(rz, "summarize_gate", gate)
        args = rz.build_parser().parse_args(argv)
        assert args.func(args) == 0
        return calls

    def test_parallel_test_sweep_feeds_build_known_failing(
            self, rz, monkeypatch):
        calls = self._run(rz, monkeypatch, ["test", "--all", "-j", "4"],
                          ["q"])
        assert calls["par"] == (["p", "q"], 4)
        assert calls["kf"] == "build"
        assert calls["gate"] == ("test", ["q"], {"q": "AGAST #1 — x"},
                                 ["p", "q"], "build")

    def test_parallel_build_sweep_feeds_gate(self, rz, monkeypatch):
        calls = self._run(rz, monkeypatch, ["build", "--all", "-j", "3"],
                          ["p"])
        assert calls["bpar"] == (["p", "q"], 3)
        assert calls["gate"][:4] == ("build", ["p"], {"q": "AGAST #1 — x"},
                                     ["p", "q"])

    def test_j1_keeps_the_serial_streaming_path(self, rz, monkeypatch):
        ran = []
        monkeypatch.setattr(rz, "run_test",
                            lambda p, extra=None: ran.append(p) or 0)
        calls = self._run(rz, monkeypatch, ["test", "--all", "-j", "1"], [])
        assert "par" not in calls
        assert ran == ["p", "q"]


@pytest.mark.unit
class TestBuildSweep:
    def test_build_units_in_order_and_failed_set(self, rz, monkeypatch,
                                                 capsys):
        def fake(unit):
            time.sleep(0.01 * (3 - unit.order[0]))
            unit.rc = 2 if unit.project == "b" else 0
            unit.output = f"[built {unit.project}]\n"
            return unit

        monkeypatch.setattr(rz, "run_unit", fake)
        failed = rz.build_projects_parallel(["a", "b", "c"], 3,
                                            ["--compiler", "ritz0"])
        assert failed == ["b"]
        out = capsys.readouterr().out
        assert out.index("[built a]") < out.index("[built b]") < out.index(
            "[built c]")
        assert "✗ b: build failed (exit 2)" in out


# --------------------------------------------------------------------------
# build.py side
# --------------------------------------------------------------------------

def _pkg(tmp_path, test_only=True, files=(), root_files=(), test_sh=False):
    pkg = tmp_path / "pkg"
    (pkg / "test").mkdir(parents=True)
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "pkg"\nversion = "0.1.0"\n'
        + ("[build]\ntest_only = true\n" if test_only else ""))
    for name, body in files:
        (pkg / "test" / name).write_text(body)
    for name, body in root_files:
        (pkg / name).write_text(body)
    if test_sh:
        (pkg / "test.sh").write_text("exit 0\n")
    return pkg


@pytest.mark.unit
class TestBuildPyUnits:
    def test_discovery_sorted_and_test_only_root_files(self, buildpy,
                                                       tmp_path):
        # Enough names, created out of order, that a directory-order glob
        # coming back sorted by accident is not plausible.
        names = [f"{c}.ritz" for c in "qmzbxakfwdoeu"]
        pkg = _pkg(tmp_path, files=[(n, "") for n in names],
                   root_files=[("test_c.ritz", ""), ("other.ritz", "")])
        cfg = {"package": {"name": "pkg"}, "build": {"test_only": True}}
        got = [p.relative_to(pkg).as_posix()
               for p in buildpy.discover_test_files(pkg, cfg)]
        assert got == [f"test/{n}" for n in sorted(names)] + ["test_c.ritz"]
        cfg = {"package": {"name": "pkg"}}
        got = [p.name for p in buildpy.discover_test_files(pkg, cfg)]
        assert got == sorted(names)

    def test_summary_counts_like_the_serial_loop(self, buildpy):
        line = buildpy.summarize_file_outcomes([
            {"status": "pass", "passed": 3, "failed": 0},
            {"status": "fail", "passed": 1, "failed": 2},
            {"status": "error", "passed": 9, "failed": 0},   # not counted
            {"status": "empty", "passed": 0, "failed": 0},
            {"status": "timeout", "passed": 0, "failed": 0},
        ])
        assert line == buildpy.format_test_summary(
            n_files=5, tests_passed=4, tests_failed=2, n_fail=1, n_error=1,
            n_empty=1, n_timeout=1)

    def test_plan_build_failure_runs_nothing(self, buildpy, tmp_path,
                                             monkeypatch):
        pkg = _pkg(tmp_path, test_only=False, files=[("a.ritz", "")],
                   test_sh=True)

        class R:
            ok = False

            def summary(self):
                return "boom"
        monkeypatch.setattr(buildpy, "build_package", lambda *a, **k: R())
        plan_path = tmp_path / "plan.json"
        rc = buildpy.unit_plan(pkg, {"package": {"name": "pkg"}}, plan_path,
                               keep_artifacts=False, use_cache=True,
                               profile_name=None, compiler="ritz0")
        assert rc == 1
        assert json.loads(plan_path.read_text()) == {
            "built": False, "no_harness": False, "files": [],
            "test_sh": False}

    def test_plan_lists_files_and_test_sh(self, buildpy, tmp_path):
        pkg = _pkg(tmp_path, files=[("a.ritz", "")], test_sh=True)
        plan_path = tmp_path / "plan.json"
        cfg = {"package": {"name": "pkg"}, "build": {"test_only": True}}
        rc = buildpy.unit_plan(pkg, cfg, plan_path, keep_artifacts=False,
                               use_cache=True, profile_name=None,
                               compiler="ritz0")
        assert rc == 0
        plan = json.loads(plan_path.read_text())
        assert plan == {"built": True, "no_harness": False,
                        "files": [str(pkg / "test" / "a.ritz")],
                        "test_sh": True}

    def test_plan_non_ritz0_is_named_no_harness_failure(self, buildpy,
                                                        tmp_path, capsys):
        pkg = _pkg(tmp_path, files=[("a.ritz", "")], test_sh=True)
        plan_path = tmp_path / "plan.json"
        cfg = {"package": {"name": "pkg"}, "build": {"test_only": True}}
        rc = buildpy.unit_plan(pkg, cfg, plan_path, keep_artifacts=False,
                               use_cache=True, profile_name=None,
                               compiler="ritz1")
        assert rc == 1
        plan = json.loads(plan_path.read_text())
        assert plan["no_harness"] and plan["files"] == [] and plan["test_sh"]
        assert "ritz1 has no --test harness; 1 test file(s) NOT run" in \
            capsys.readouterr().out


# --------------------------------------------------------------------------
# End to end: one real package, serial build.py vs the rz pool
# --------------------------------------------------------------------------

PASS_SRC = "[[test]]\nfn test_ok() -> i32\n    assert 1 + 1 == 2\n    0\n"
FAIL_SRC = "[[test]]\nfn test_bad() -> i32\n    assert 1 + 1 == 3\n    0\n"
EMPTY_SRC = "fn helper() -> i32\n    0\n"


@pytest.mark.integration
def test_pool_verdict_lines_match_serial_build_py(rz, tmp_path, capsys):
    """The ticket's acceptance property, on a package small enough to run in
    the unit gate: same exit verdict, same per-file lines, same Σ line."""
    import subprocess
    pkg = _pkg(tmp_path, files=[("t_pass.ritz", PASS_SRC),
                                ("t_fail.ritz", FAIL_SRC),
                                ("t_empty.ritz", EMPTY_SRC)])
    serial = subprocess.run(
        [sys.executable, str(rz.RITZ_BUILD), "test", str(pkg)],
        env=rz.child_env(str(pkg)), cwd=rz.WORKSPACE_ROOT,
        capture_output=True, text=True, timeout=600)

    failed = rz.test_projects_parallel([str(pkg)], 3, "ritz0")
    pooled = capsys.readouterr().out

    verdict = lambda s: [l for l in s.splitlines()  # noqa: E731
                         if l.startswith(("    ✓", "    ✗", "    ⏱", "  Σ"))]
    assert serial.returncode == 1 and failed == [str(pkg)]
    assert verdict(pooled) == verdict(serial.stdout)
    assert len(verdict(pooled)) == 4, pooled
