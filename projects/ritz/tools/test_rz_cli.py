"""Tests for the workspace-level `rz` CLI (AGAST #1324).

Why these tests live here: `rz` sits at the workspace root with no test
suite of its own, while CI's bootstrap job already runs `make tools-unit`
(pytest over projects/ritz/tools/). Importing the script by path from here
puts the gate logic under the only pytest umbrella that actually runs in CI.

What broke and what these tests pin down:

1. `rz test --all` in CI printed every "Testing: <project>" banner
   back-to-back with no diagnostics between them. The diagnostics existed —
   they were emitted by the build.py children — but the parent's banners
   were block-buffered (stdout was a pipe) while each child flushed at
   exit, so the log showed orphaned diagnostics followed by a wall of
   banners. The fix is (a) flush banners before spawning the child and
   (b) run children with PYTHONUNBUFFERED so grandchild output interleaves
   correctly too. `_child_env` is the tested seam for (b).

2. The gate itself: build-all/test-all had been red for 12+ runs, which is
   a disabled gate. The replacement is an explicit, named, per-project
   known-failing list: `gate = "build"` entries in known-failures/ (there
   is deliberately no test gate), each citing an AGAST task, validated at
   load time by tools/known_failures.py, whose `outcome` is the one
   classification (AGAST #1834): hard failures gate, known failures are
   advisory-but-visible, and a known-failing project that PASSES also gates
   (strict xpass — stale entries are forced out; new entries are a
   review-time concern).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# rz is an extensionless executable script three levels up from tools/.
RZ_PATH = Path(__file__).resolve().parents[3] / "rz"


@pytest.fixture(scope="module")
def rz():
    spec = importlib.util.spec_from_loader(
        "rz_cli", importlib.machinery.SourceFileLoader("rz_cli", str(RZ_PATH))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def buildpy(request):
    # build.py does `from cache import BuildCache`, so its own directory
    # must be importable while we exec it by path.
    pkg_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(pkg_dir))
    request.addfinalizer(lambda: sys.path.remove(str(pkg_dir)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy", pkg_dir / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
class TestChildEnv:
    def test_child_env_is_unbuffered(self, rz, monkeypatch):
        # The CI-illegibility bug: buffered children detach diagnostics
        # from their banners. Every child must run unbuffered.
        # delenv first: many dev shells and agent harnesses export
        # PYTHONUNBUFFERED=1 themselves, and child_env copies os.environ —
        # without this the test passes even if the feature is deleted.
        monkeypatch.delenv("PYTHONUNBUFFERED", raising=False)
        env = rz.child_env("ritz")
        assert env.get("PYTHONUNBUFFERED") == "1"

    def test_child_env_has_ritz_path_with_ritz(self, rz):
        env = rz.child_env("ritz")
        assert "RITZ_PATH" in env
        assert any(Path(p).name == "ritz" for p in env["RITZ_PATH"].split(":")), (
            "RITZ_PATH must include projects/ritz for ritzlib resolution"
        )


@pytest.mark.unit
class TestKnownFailingConfig:
    """rz reads its excuses through tools/known_failures.py, the one parser
    and outcome rule (AGAST #1834). The rules themselves (AGAST id, no test
    gate, strict xpass) are pinned once, in tools/test_known_failures.py;
    these pin that rz is wired to them."""

    @staticmethod
    def _kf_dir(tmp_path, monkeypatch, text):
        (tmp_path / "7.toml").write_text(text)
        monkeypatch.setenv("RITZ_KNOWN_FAILURES", str(tmp_path))

    def test_build_entries_are_the_excuses(self, rz, tmp_path, monkeypatch):
        self._kf_dir(tmp_path, monkeypatch,
                     '[[entry]]\ngate = "build"\ncompiler = "any"\nunit = "lexis"\n'
                     'reason = "why"\nagast = 7\n'
                     '[[entry]]\ngate = "matrix"\ncompiler = "ritz1"\nunit = "t"\n'
                     'reason = "not rz\'s"\nagast = 7\n')
        assert rz.known_failing_from_config() == {"lexis": "AGAST #7: why"}

    def test_the_sweep_reads_its_compilers_build_excuses(self, rz, tmp_path,
                                                         monkeypatch):
        """AGAST #4272: `rz build --all --compiler ritz1` honours a ritz1
        build entry; the ritz0 sweep does not."""
        self._kf_dir(tmp_path, monkeypatch,
                     '[[entry]]\ngate = "build"\ncompiler = "ritz1"\nunit = "x"\n'
                     'reason = "r1"\nagast = 7\n')
        assert rz.known_failing_from_config("ritz1") == {"x": "AGAST #7: r1"}
        assert rz.known_failing_from_config("ritz0") == {}

    def test_the_ritz1_test_sweep_also_reads_parity_excuses(self, rz, tmp_path,
                                                            monkeypatch):
        """AGAST #4591: a package that builds under ritz1 but whose tests fail
        there is a `parity` entry.  Only the test sweep under that compiler
        reads it: the build sweep would xpass-fail on it, and ritz0's test
        sweep is the reference, never excused."""
        self._kf_dir(tmp_path, monkeypatch,
                     '[[entry]]\ngate = "build"\ncompiler = "ritz1"\nunit = "x"\n'
                     'reason = "r1"\nagast = 7\n'
                     '[[entry]]\ngate = "parity"\ncompiler = "ritz1"\nunit = "y"\n'
                     'reason = "p1"\nagast = 7\n')
        assert rz.known_failing_from_config("ritz1", kind="test") == {
            "x": "AGAST #7: r1", "y": "AGAST #7: p1"}
        assert rz.known_failing_from_config("ritz1") == {"x": "AGAST #7: r1"}
        assert rz.known_failing_from_config("ritz0", kind="test") == {}
        assert rz.known_failing_from_config("ritz1_selfhosted", kind="test") == {}

    def test_a_malformed_excuse_stops_rz(self, rz, tmp_path, monkeypatch, capsys):
        # No ticket: rz refuses rather than honouring it.
        self._kf_dir(tmp_path, monkeypatch,
                     '[[entry]]\ngate = "build"\ncompiler = "any"\nunit = "lexis"\n'
                     'reason = "why"\n')
        with pytest.raises(SystemExit) as e:
            rz.known_failing_from_config()
        assert e.value.code == 2
        assert "7.toml" in capsys.readouterr().err

    def test_the_real_list_loads(self, rz):
        assert isinstance(rz.known_failing_from_config(), dict)

    def test_summary_classifies_with_the_shared_outcome(self, rz, monkeypatch):
        calls = []
        real = rz.known_failures.outcome

        def spy(*a, **k):
            calls.append(a)
            return real(*a, **k)
        monkeypatch.setattr(rz.known_failures, "outcome", spy)
        rz.summarize_gate("build", ["a"], {}, ["a"])
        assert calls

    def test_a_synthetic_xpass_fails_both_sweeps(self, rz, tmp_path, monkeypatch):
        """#1834 acceptance: an excused project that builds fails the gate,
        through the real loader, for the build and the test sweep."""
        self._kf_dir(tmp_path, monkeypatch,
                     '[[entry]]\ngate = "build"\ncompiler = "any"\nunit = "a"\n'
                     'reason = "why"\nagast = 7\n')
        for kind in ("build", "test"):
            assert rz.summarize_gate(kind, [], rz.known_failing_from_config(),
                                     ["a", "b"]) == 1

    def test_gate_summary_exit_codes(self, rz):
        # summarize_gate returns the job exit code: hard failures and
        # stale exclusions gate; known failures alone do not.
        assert rz.summarize_gate("test", [], {}, ["a"]) == 0
        assert rz.summarize_gate("test", ["a"], {}, ["a"]) == 1
        assert rz.summarize_gate("test", ["a"], {"a": "AGAST #0"}, ["a"]) == 0
        assert rz.summarize_gate("test", [], {"a": "AGAST #0"}, ["a"]) == 1

    def test_setup_error_is_its_own_verdict(self, rz, capsys):
        # AGAST #2141: a project whose build exited EXIT_SETUP (a missing
        # tool, e.g. harland without lld-link) is neither a pass nor a
        # regression. Alone it exits 3; named under SETUP ERROR, not under
        # "Failed build".
        rc = rz.summarize_gate("build", ["harland"], {}, ["harland", "a"],
                               setup=["harland"])
        out = capsys.readouterr().out
        assert rc == rz.EXIT_SETUP == 3
        assert "SETUP ERROR" in out and "harland" in out
        assert "Failed build" not in out

    def test_setup_error_never_masks_a_regression(self, rz, capsys):
        rc = rz.summarize_gate("build", ["harland", "angelo"], {},
                               ["harland", "angelo"], setup=["harland"])
        out = capsys.readouterr().out
        assert rc == 1
        assert "✗ Failed build: angelo" in out
        assert "SETUP ERROR" in out

    def test_setup_error_on_a_known_failing_project_stays_advisory(self, rz):
        # Already excused: the setup miss does not make it gate.
        assert rz.summarize_gate("build", ["lexis"], {"lexis": "AGAST #0"},
                                 ["lexis"], setup=["lexis"]) == 0

    def test_build_sweep_collects_setup_exit_codes(self, rz, monkeypatch):
        # The parallel sweep (the gate's path: rz.toml max_jobs = 8) hands
        # summarize_gate the projects whose build exited EXIT_SETUP.
        def fake_pool(jobs, units, on_done):
            for u in units:
                u.rc = {"harland": 3, "angelo": 1}.get(u.project, 0)
                u.output = ""
                on_done(u)
        monkeypatch.setattr(rz, "run_pool", fake_pool)
        failed, setup = rz.build_projects_parallel(
            ["angelo", "harland", "ok"], 2, ["--compiler", "ritz0"])
        assert failed == ["angelo", "harland"]
        assert setup == ["harland"]

    def test_gate_summary_names_the_source_list(self, rz, capsys):
        # The test sweep borrows the BUILD entries; the summary must point
        # readers at where the excuse actually lives.
        rz.summarize_gate("test", ["a"], {"a": "AGAST #0 x"}, ["a"])
        out = capsys.readouterr().out
        assert 'known-failures/ (gate = "build")' in out

    def test_gate_summary_has_one_verdict_line_per_package(self, rz, capsys):
        # AGAST #3969: the room gate runs `rz test --all`, and its log must
        # say what happened to EACH package, in the `PKG <VERDICT> <id>`
        # form train.sh's package step already prints (run-gate.sh --wait
        # greps `^PKG `). Passes first, then the lines that matter, so a
        # FAIL survives the --wait summary's `tail -20`.
        rz.summarize_gate("test", ["bad", "old", "nomake"],
                          {"old": "AGAST #1 compile", "stale": "AGAST #2"},
                          ["ok", "bad", "old", "stale", "nomake", "ok2"],
                          setup=["nomake"])
        pkg = [line for line in capsys.readouterr().out.splitlines()
               if line.startswith("PKG ")]
        assert pkg == [
            "PKG PASS ok",
            "PKG PASS ok2",
            "PKG KNOWN old: AGAST #1 compile",
            'PKG XPASS stale: excused in known-failures/ (gate = "build") but passed',
            "PKG SETUP nomake: a missing tool, not a regression",
            "PKG FAIL bad",
        ], pkg

    def test_gate_summary_verdict_lines_on_a_clean_sweep(self, rz, capsys):
        assert rz.summarize_gate("build", [], {}, ["b", "a"]) == 0
        pkg = [line for line in capsys.readouterr().out.splitlines()
               if line.startswith("PKG ")]
        assert pkg == ["PKG PASS b", "PKG PASS a"]


@pytest.mark.unit
class TestBuildPyRitzPathForTests:
    """build.py's run_tests RITZ_PATH seam (AGAST #1324 review fix).

    Resolution is first-match-wins, so ROOT must come FIRST: a leaked
    RITZ_PATH from a parent shell may point at a different worktree, and
    under direct invocation (`python3 build.py test ...`, `make test`)
    its ritzlib must not shadow this tree's. This matches the ritz1
    compile-step ordering in the same file.
    """

    def test_root_comes_first(self, buildpy):
        root = str(buildpy.ROOT.resolve())
        result = buildpy.ritz_path_for_tests("/some/other/worktree/ritz")
        assert result.split(":")[0] == root
        assert result.split(":")[1] == "/some/other/worktree/ritz"

    def test_empty_caller_path_yields_just_root(self, buildpy):
        assert buildpy.ritz_path_for_tests("") == str(buildpy.ROOT.resolve())

    def test_duplicate_root_is_deduplicated_even_unresolved(self, buildpy):
        # An unresolved/relative spelling of ROOT must not survive as a
        # second entry (the old `not in _parts` check compared strings).
        unresolved = str(buildpy.ROOT) + "/."
        result = buildpy.ritz_path_for_tests(unresolved)
        assert result == str(buildpy.ROOT.resolve())

    def test_caller_order_is_preserved_after_root(self, buildpy):
        result = buildpy.ritz_path_for_tests("/a:/b")
        assert result.split(":")[1:] == ["/a", "/b"]


@pytest.mark.unit
class TestSurvey:
    """`rz test rllvm --survey DIR [--profile P]` (AGAST #4807): builds rllvm,
    then runs its survey.py over DIR with that binary. It builds no IR."""

    def run(self, rz, monkeypatch, argv, build_rc=0):
        calls = []
        monkeypatch.setattr(rz, "run_build",
                            lambda p, extra=None: calls.append(("build", p, extra)) or build_rc)

        class Done:
            returncode = 7

        def child(cmd, env=None, cwd=None):
            calls.append(("child", cmd, env))
            return Done()
        monkeypatch.setattr(rz.bounded_run, "child", child)
        args = rz.build_parser().parse_args(argv)
        return args.func(args), calls

    def test_builds_rllvm_then_runs_the_survey_on_dir(self, rz, monkeypatch, tmp_path):
        rc, calls = self.run(rz, monkeypatch, ["test", "rllvm", "--survey", str(tmp_path),
                                               "--profile", "kernel", "--compiler", "ritz1"])
        assert rc == 7
        assert calls[0] == ("build", "rllvm", ["--compiler", "ritz1"])
        _, cmd, env = calls[1]
        assert cmd[1:] == [str(rz.PROJECTS_DIR / "rllvm" / "tests" / "survey.py"),
                           str(tmp_path.resolve()), "--profile", "kernel"]
        assert env["RLLVM"] == str(rz.PROJECTS_DIR / "rllvm" / "build" / "debug" / "rllvm")

    def test_profile_defaults_to_hosted(self, rz, monkeypatch, tmp_path):
        _, calls = self.run(rz, monkeypatch, ["test", "rllvm", "--survey", str(tmp_path)])
        assert calls[1][1][-2:] == ["--profile", "hosted"]

    def test_a_failed_build_runs_no_survey(self, rz, monkeypatch, tmp_path):
        rc, calls = self.run(rz, monkeypatch, ["test", "rllvm", "--survey", str(tmp_path)],
                             build_rc=1)
        assert rc == 1 and [c[0] for c in calls] == ["build"]

    @pytest.mark.parametrize("argv", [["test", "razm", "--survey", "x"],
                                      ["test", "--all", "--survey", "x"]])
    def test_survey_is_rllvms_alone(self, rz, monkeypatch, capsys, argv):
        rc, calls = self.run(rz, monkeypatch, argv)
        assert rc == 1 and calls == []
        assert "--survey runs rllvm's survey" in capsys.readouterr().err
