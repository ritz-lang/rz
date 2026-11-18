#!/usr/bin/env python3
"""Self-tests for ci_local.py — AGAST #1363.

The point of ci_local.py is that it cannot drift from CI, because it parses
main.yml rather than restating it. These tests hold it to that:

  * every `run:` step in the workflow is enumerated — a runner that silently
    drops a step is a green tick asserting less than you think, which is the
    exact failure this tool exists to prevent
  * `working-directory` is honoured even when declared AFTER the `run:` block,
    which is the layout that made a `grep -A 6` produce a confident wrong
    claim about what CI executes (#1363's own retraction)
  * setup steps are reported when skipped, never silently omitted
  * the real main.yml parses and yields the jobs we expect

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_local.py -q
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ci_local  # noqa: E402


# --------------------------------------------------------------------------
# A real (non --dry-run) main() ends by trimming the artifact store and sets
# RITZ_CAS_STATS_LOG in os.environ for its steps (right for a gate process).
# In a test that meant gc() on the machine's shared ~/.cache/ritz/cas, run
# concurrently by every xdist worker while other workers' builds read from it,
# and a stats log leaked into the rest of the session (AGAST #2792).
# --------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def private_cas(tmp_path, monkeypatch):
    store = tmp_path / "cas"
    monkeypatch.setenv("RITZ_CACHE_DIR", str(store))
    # "" reads as unset to main(); setenv's undo restores the session's value
    # over whatever main() writes to os.environ.
    monkeypatch.setenv("RITZ_CAS_STATS_LOG", "")
    return store


# --------------------------------------------------------------------------
# Against the real workflow
# --------------------------------------------------------------------------

def test_real_workflow_exists():
    assert ci_local.WORKFLOW.is_file(), (
        f"workflow not found at {ci_local.WORKFLOW}; REPO_ROOT resolution is wrong"
    )


def test_every_run_step_is_enumerated():
    """No step may be dropped between the YAML and the runner."""
    spec = yaml.safe_load(ci_local.WORKFLOW.read_text())
    expected = sum(
        1
        for jobspec in spec["jobs"].values()
        for s in (jobspec.get("steps") or [])
        if "run" in s
    )
    assert len(ci_local.load_steps()) == expected


def test_no_uses_only_step_is_enumerated():
    """Checkout/setup-python have no shell command and must not be run."""
    for s in ci_local.load_steps():
        assert s.run, f"{s} has an empty command"


def test_pytest_step_carries_its_working_directory():
    """The specific fact a grep got wrong: this step is NOT run from the root."""
    steps = [s for s in ci_local.load_steps() if "unit tests" in s.name.lower()
             and "ritz0" in s.name.lower()]
    assert steps, "could not find the ritz0 unit tests step"
    assert steps[0].workdir == "projects/ritz/ritz0", (
        f"expected projects/ritz/ritz0, got {steps[0].workdir!r}"
    )


def test_default_job_is_declared_by_the_workflow():
    assert ci_local.DEFAULT_JOB in ci_local.jobs_in(ci_local.load_steps())


# --------------------------------------------------------------------------
# Against a synthetic workflow, so these can actually go red
# --------------------------------------------------------------------------

WORKDIR_AFTER_RUN = """\
jobs:
  alpha:
    steps:
      - uses: actions/checkout@v4
      - name: Install toolchain
        run: echo installing
      - name: Real gate
        run: echo gating
        working-directory: projects/ritz/ritz0
  beta:
    steps:
      - name: Beta step
        run: echo beta
"""


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    wf = tmp_path / "main.yml"
    wf.write_text(WORKDIR_AFTER_RUN)
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    return wf


def test_working_directory_declared_after_run_is_picked_up(synthetic):
    steps = ci_local.load_steps(synthetic)
    gate = next(s for s in steps if s.name == "Real gate")
    assert gate.workdir == "projects/ritz/ritz0"


def test_uses_step_is_excluded(synthetic):
    names = [s.name for s in ci_local.load_steps(synthetic)]
    assert names == ["Install toolchain", "Real gate", "Beta step"]


def test_setup_steps_are_identified(synthetic):
    steps = ci_local.load_steps(synthetic)
    assert [s.is_setup for s in steps] == [True, False, False]


def test_jobs_are_reported_in_declaration_order(synthetic):
    assert ci_local.jobs_in(ci_local.load_steps(synthetic)) == ["alpha", "beta"]


def test_skipped_setup_steps_are_printed_not_silent(synthetic, capsys, monkeypatch):
    monkeypatch.setattr(ci_local, "REPO_ROOT", Path("/"))
    ci_local.main(["--job", "alpha", "--dry-run"])
    out = capsys.readouterr().out
    assert "Install toolchain" in out, "a skipped step was omitted silently"
    assert "skipped" in out.lower()


def test_unknown_job_is_an_error(synthetic, capsys):
    assert ci_local.main(["--job", "nope"]) == 2
    assert "unknown job" in capsys.readouterr().err


def test_list_prints_every_step(synthetic, capsys):
    assert ci_local.main(["--list"]) == 0
    out = capsys.readouterr().out
    for name in ("Install toolchain", "Real gate", "Beta step", "alpha", "beta"):
        assert name in out


def test_missing_working_directory_is_named_not_left_to_the_shell(tmp_path, monkeypatch, capsys):
    """The 127/2 class of failure, reported as itself.

    A bad path used to surface as `exit 127` from bash, which reads like a test
    suite complaining about something pre-existing rather than a command that
    never ran.
    """
    wf = tmp_path / "main.yml"
    wf.write_text("""\
jobs:
  alpha:
    steps:
      - name: Bad dir
        run: echo hi
        working-directory: does/not/exist
""")
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    monkeypatch.setattr(ci_local, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ci_local, "DEFAULT_JOB", "alpha")
    assert ci_local.main([]) == 1
    err = capsys.readouterr().err
    assert "working-directory does not exist" in err


# --------------------------------------------------------------------------
# AGAST #1802: fail-fast, per-step timing, ritz1 built before pytest
# --------------------------------------------------------------------------

THREE_STEPS = """\
jobs:
  alpha:
    steps:
      - name: First ok
        run: echo first
      - name: Second fails
        run: exit 4
      - name: Third leaves a marker
        run: touch {marker}
"""


@pytest.fixture
def three_steps(tmp_path, monkeypatch):
    marker = tmp_path / "third-ran"
    wf = tmp_path / "main.yml"
    wf.write_text(THREE_STEPS.format(marker=marker))
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    monkeypatch.setattr(ci_local, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ci_local, "DEFAULT_JOB", "alpha")
    return marker


@pytest.mark.integration
def test_fail_fast_stops_at_the_first_failing_step(three_steps, capsys):
    """A broken compiler must not cost the whole gate (design §5)."""
    assert ci_local.main(["--fail-fast"]) == 1
    assert not three_steps.exists(), "--fail-fast ran a step after a failure"
    out = capsys.readouterr().out
    # Steps that never ran are named, never silently dropped.
    assert "not run" in out and "Third leaves a marker" in out


@pytest.mark.integration
def test_without_fail_fast_every_step_runs(three_steps):
    """Default keeps per-step semantics: a failure is recorded, later steps run."""
    assert ci_local.main([]) == 1
    assert three_steps.exists()


@pytest.mark.integration
def test_a_real_run_trims_this_tests_store_not_the_shared_one(
        three_steps, private_cas, capsys):
    """AGAST #2792. Fails without `private_cas`: alone, the gc line names
    ~/.cache/ritz/cas; after another real main() on the same worker, the
    leaked RITZ_CAS_STATS_LOG suppresses the trim and there is no gc line."""
    ci_local.main([])
    gc = [ln for ln in capsys.readouterr().out.splitlines()
          if ln.startswith("[ritz-cas] gc:")]
    assert gc == [f"[ritz-cas] gc: removed 0 files, freed 0 bytes from {private_cas}"]


@pytest.mark.integration
def test_each_step_prints_start_and_end_with_duration(three_steps, capsys):
    ci_local.main([])
    out = capsys.readouterr().out
    iso = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d"
    for name, rc in (("First ok", 0), ("Second fails", 4),
                     ("Third leaves a marker", 0)):
        assert re.search(rf"\[{re.escape(name)}\] START {iso}", out), out
        assert re.search(
            rf"\[{re.escape(name)}\] END {iso}\S* \d+(\.\d+)?s rc={rc}\b", out), out


@pytest.mark.integration
def test_final_timing_table_lists_every_step_run(three_steps, capsys):
    ci_local.main(["--fail-fast"])
    out = capsys.readouterr().out
    table = out[out.index("step timings"):]
    assert re.search(r"First ok\s+\d+(\.\d+)?s\s+rc=0", table), table
    assert re.search(r"Second fails\s+\d+(\.\d+)?s\s+rc=4", table), table
    assert re.search(r"total\s+\d+(\.\d+)?s", table), table


# --------------------------------------------------------------------------
# AGAST #1897: --skip <step>, so run-gate's up-front smoke is not repeated.
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_skip_does_not_run_the_named_step(three_steps, capsys):
    assert ci_local.main(["--skip", "Second fails"]) == 0
    assert three_steps.exists(), "--skip stopped later steps from running"
    out = capsys.readouterr().out
    assert "[Second fails] START" not in out
    # Named in the summary, never silently dropped.
    summary = out[out.index("skipped (--skip)"):]
    assert "Second fails" in summary


@pytest.mark.integration
def test_skip_is_repeatable(three_steps, capsys):
    assert ci_local.main(["--skip", "Second fails",
                          "--skip", "Third leaves a marker"]) == 0
    assert not three_steps.exists()
    out = capsys.readouterr().out
    assert "[First ok] START" in out


def test_skip_of_an_unknown_step_fails_before_running_anything(three_steps, capsys):
    """A renamed step must not turn the skip into a silent no-op."""
    assert ci_local.main(["--skip", "Second fail"]) == 2
    assert not three_steps.exists()
    captured = capsys.readouterr()
    assert "[First ok] START" not in captured.out
    assert "'Second fail'" in captured.err
    assert "Second fails" in captured.err, "valid step names should be listed"


def test_skip_must_name_a_step_in_the_selected_job(tmp_path, monkeypatch, capsys):
    wf = tmp_path / "main.yml"
    wf.write_text("jobs:\n  alpha:\n    steps:\n      - name: A\n        run: 'true'\n"
                  "  beta:\n    steps:\n      - name: B\n        run: 'true'\n")
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    monkeypatch.setattr(ci_local, "REPO_ROOT", tmp_path)
    assert ci_local.main(["--job", "alpha", "--skip", "B"]) == 2


def test_real_bootstrap_job_has_the_step_the_gate_skips():
    names = [s.name for s in ci_local.load_steps() if s.job == ci_local.DEFAULT_JOB]
    assert "Smoke" in names, names


def test_ritz1_is_built_before_pytest_in_the_bootstrap_job():
    """pytest's ~80 module fixtures must find ritz1 already built, not each
    race a cold serial build (design §2)."""
    names = [s.name for s in ci_local.load_steps() if s.job == "bootstrap"]
    build = [i for i, n in enumerate(names)
             if "build ritz1" in n.lower() and "selfhosted" in n.lower()]
    pytest_ix = [i for i, n in enumerate(names)
                 if "ritz0 unit tests" in n.lower()]
    assert build and pytest_ix, names
    assert build[0] < pytest_ix[0], names


def test_ritz1_build_step_is_parallel():
    step = next(s for s in ci_local.load_steps()
                if s.job == "bootstrap" and "build ritz1" in s.name.lower())
    assert "ritz1-bootstrap" in step.run or "-j" in step.run, step.run


def test_gate_runner_defaults_to_fail_fast():
    gate = ci_local.REPO_ROOT / ".claude/skills/rz-iterate/run-gate.sh"
    if not gate.is_file():
        pytest.skip("run-gate.sh is not part of this checkout")
    cmd_line = next(line for line in gate.read_text().splitlines()
                    if line.startswith("CMD="))
    assert re.search(r"ci-local ARGS=\S*--fail-fast", cmd_line), cmd_line


def test_gate_runner_runs_build_all_test_all_and_bootstrap():
    """AGAST #2141: #2124 broke angelo, passed a bootstrap-only gate, and
    turned main's build-all red. The gate runs both jobs. AGAST #3969
    (Aaron 2026-11-18): it runs main.yml's test-all job too, so a package
    test break fails the gate instead of CI after the push to main."""
    gate = ci_local.REPO_ROOT / ".claude/skills/rz-iterate/run-gate.sh"
    if not gate.is_file():
        pytest.skip("run-gate.sh is not part of this checkout")
    text = gate.read_text()
    cmd_line = next(line for line in text.splitlines() if line.startswith("CMD="))
    args = re.search(r'ci-local ARGS=\\"([^"\\]*)\\"', cmd_line)
    assert args, cmd_line
    jobs = re.findall(r"--job (\S+)", args.group(1))
    assert set(jobs) == {"build-all", "test-all", "bootstrap"}, cmd_line
    # The gate runs the job CI runs, not a copy of its command.
    assert "test-all" in ci_local.jobs_in(ci_local.load_steps())
    # --wait's summary must surface the verdicts: which project broke, and a
    # setup error as itself.
    wait_grep = next(line for line in text.splitlines()
                     if "grep -E" in line and "EXIT" in line)
    for needle in ("Failed build", "SETUP ERROR", "^PKG "):
        assert needle in wait_grep, wait_grep


# --------------------------------------------------------------------------
# AGAST #1907: the gate must see CI's environment, not just CI's commands.
#
# #1805's gate passed and CI went red on the same commit: CI's
# setup action (then install-toolchain) puts /usr/lib/llvm-21/bin on PATH (so `opt` and
# `llvm-as` exist), ci_local dropped that `uses:` step without a trace, and
# TestIRVerification skipped locally instead of tripping the spawn guard.
# Step `env:` (RITZ_VERIFY_IR=1) was dropped the same way.
# --------------------------------------------------------------------------

TOOLCHAIN_WF = """\
env:
  CLANG_VERSION: '77'
  FOO: workflow
jobs:
  alpha:
    env:
      BAR: job
    steps:
      - name: Before toolchain
        run: test "$(command -v opt || true)" != "{bindir}/opt"
      - name: Python (not the toolchain, though its path contains actions/setup)
        uses: actions/setup-python@v5
      - name: Still unpinned
        run: test "$(command -v opt || true)" != "{bindir}/opt"
      - name: Set up Python, toolchain and ritz0 dependencies
        uses: ./.github/actions/setup
        with:
          clang-version: ${{{{ env.CLANG_VERSION }}}}
      - name: Sees pinned opt
        run: test "$(command -v opt)" = "{bindir}/opt"
      - name: Sees merged env
        run: test "$FOO" = step && test "$BAR" = job && test "$CLANG_VERSION" = 77
        env:
          FOO: step
"""


@pytest.fixture
def toolchain_wf(tmp_path, monkeypatch):
    bindir = tmp_path / "llvm-77" / "bin"
    bindir.mkdir(parents=True)
    opt = bindir / "opt"
    opt.write_text("#!/bin/sh\nexit 0\n")
    opt.chmod(0o755)
    wf = tmp_path / "main.yml"
    wf.write_text(TOOLCHAIN_WF.format(bindir=bindir))
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    monkeypatch.setattr(ci_local, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ci_local, "DEFAULT_JOB", "alpha")
    monkeypatch.setattr(ci_local, "LLVM_BINDIR", str(tmp_path / "llvm-{version}" / "bin"))
    return bindir


def test_steps_after_the_setup_action_get_the_pinned_bindir(toolchain_wf):
    steps = {s.name: s for s in ci_local.load_steps()}
    assert steps["Before toolchain"].llvm_bindir is None
    assert steps["Still unpinned"].llvm_bindir is None
    assert steps["Sees pinned opt"].llvm_bindir == str(toolchain_wf)


@pytest.mark.integration
def test_pinned_toolchain_is_on_path_when_steps_run(toolchain_wf, capsys):
    """The #1907 miss: TestIRVerification needs `opt` on PATH, as in CI."""
    assert ci_local.main([]) == 0, capsys.readouterr().out


@pytest.mark.integration
def test_missing_pinned_bindir_fails_loudly(toolchain_wf, capsys):
    """A gate without the pinned toolchain asserts less than CI: say so."""
    for f in toolchain_wf.iterdir():
        f.unlink()
    toolchain_wf.rmdir()
    assert ci_local.main(["--job", "alpha"]) == 1
    assert str(toolchain_wf) in capsys.readouterr().err


def test_workflow_job_and_step_env_are_merged_like_ci(toolchain_wf):
    step = next(s for s in ci_local.load_steps() if s.name == "Sees merged env")
    assert step.env == {"CLANG_VERSION": "77", "FOO": "step", "BAR": "job"}


def test_real_bootstrap_job_pins_the_workflow_clang():
    wf = yaml.safe_load(ci_local.WORKFLOW.read_text())
    version = str(wf["env"]["CLANG_VERSION"])
    pytest_step = next(s for s in ci_local.load_steps()
                       if s.job == "bootstrap" and s.name == "ritz0 unit tests")
    assert pytest_step.llvm_bindir == ci_local.LLVM_BINDIR.format(version=version)


@pytest.mark.integration
def test_step_does_not_inherit_makefile_ritz_path(monkeypatch, tmp_path):
    """AGAST #4150: `make ci-local` exports RITZ_PATH; CI's steps never see it.

    Leaking it made the gate pass a test that resolves ritzlib only through
    RITZ_PATH, while CI failed it.  A step's own `env:` may still set it.
    """
    monkeypatch.setenv("RITZ_PATH", "/leaked/from/make")
    out = tmp_path / "seen"
    run = f'printf "%s" "${{RITZ_PATH-unset}}" > {out}'
    assert ci_local.run_step(ci_local.Step("j", "n", run, ".")) == 0
    assert out.read_text() == "unset"
    step = ci_local.Step("j", "n", run, ".", env={"RITZ_PATH": "/declared"})
    assert ci_local.run_step(step) == 0
    assert out.read_text() == "/declared"


def test_real_verify_ir_steps_carry_their_env():
    verified = [s.name for s in ci_local.load_steps()
                if s.job == "bootstrap" and s.env.get("RITZ_VERIFY_IR") == "1"]
    assert len(verified) >= 2, verified


# --------------------------------------------------------------------------
# AGAST #2141: the gate runs build-all AND bootstrap; a setup error is its
# own verdict, never folded into "failed" (1) or "passed" (0).
# --------------------------------------------------------------------------

TWO_JOBS = """\
jobs:
  alpha:
    steps:
      - name: A
        run: {a}
  beta:
    steps:
      - name: B
        run: {b}
"""


def _two_jobs(tmp_path, monkeypatch, a="'true'", b="'true'"):
    wf = tmp_path / "main.yml"
    wf.write_text(TWO_JOBS.format(a=a, b=b))
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    monkeypatch.setattr(ci_local, "REPO_ROOT", tmp_path)


@pytest.mark.integration
def test_job_is_repeatable(tmp_path, monkeypatch, capsys):
    _two_jobs(tmp_path, monkeypatch)
    assert ci_local.main(["--job", "alpha", "--job", "beta"]) == 0
    out = capsys.readouterr().out
    assert "[A] START" in out and "[B] START" in out
    assert "all steps passed for: alpha, beta" in out


@pytest.mark.integration
def test_repeated_job_runs_in_workflow_order(tmp_path, monkeypatch, capsys):
    _two_jobs(tmp_path, monkeypatch)
    ci_local.main(["--job", "beta", "--job", "alpha"])
    out = capsys.readouterr().out
    assert out.index("[A] START") < out.index("[B] START")


def test_unknown_job_among_several_is_an_error(tmp_path, monkeypatch):
    _two_jobs(tmp_path, monkeypatch)
    assert ci_local.main(["--job", "alpha", "--job", "nope"]) == 2


@pytest.mark.integration
def test_setup_only_failure_exits_with_the_setup_code(tmp_path, monkeypatch, capsys):
    _two_jobs(tmp_path, monkeypatch, a="exit 3")
    assert ci_local.main(["--job", "alpha", "--job", "beta"]) == ci_local.EXIT_SETUP == 3
    out = capsys.readouterr().out
    assert "SETUP ERROR" in out


@pytest.mark.integration
def test_real_failure_beats_a_setup_error(tmp_path, monkeypatch):
    _two_jobs(tmp_path, monkeypatch, a="exit 3", b="exit 1")
    assert ci_local.main(["--job", "alpha", "--job", "beta"]) == 1


@pytest.mark.integration
def test_setup_error_does_not_stop_fail_fast(tmp_path, monkeypatch, capsys):
    # A missing tool says nothing about the compiler: the bootstrap job
    # still runs, so the gate's verdict on the code is complete.
    _two_jobs(tmp_path, monkeypatch, a="exit 3", b="exit 1")
    assert ci_local.main(["--fail-fast", "--job", "alpha", "--job", "beta"]) == 1
    assert "[B] START" in capsys.readouterr().out


# AGAST #3624: pytest exits 3 too -- INTERNALERROR, a conftest or plugin
# crash. The ritz0 step passes it straight through (`pytest | tee` under
# pipefail), so a crashed session read as "a missing tool", skipped
# --fail-fast and ran the gate on for ~10 minutes.
CRASHING_CONFTEST = "def pytest_collection_modifyitems(items):\n    raise RuntimeError('boom')\n"


@pytest.mark.integration
def test_pytest_internalerror_is_a_failure_not_a_setup_error(tmp_path, monkeypatch, capsys):
    # A real pytest crash, not a stub: pins that pytest's code for it is
    # the one build.py uses for a missing tool.
    (tmp_path / "conftest.py").write_text(CRASHING_CONFTEST)
    (tmp_path / "test_x.py").write_text("def test_x():\n    pass\n")
    _two_jobs(tmp_path, monkeypatch,
              a=f"'{sys.executable} -m pytest -q -p no:cacheprovider --disable-plugin-autoload'",
              b="'true'")
    assert ci_local.main(["--fail-fast", "--job", "alpha", "--job", "beta"]) == 1
    out = capsys.readouterr().out
    assert "failed:\n  - [alpha] A (exit 3)" in out and "SETUP ERROR" not in out
    assert "[B] START" not in out  # --fail-fast stopped the gate


def test_only_non_pytest_steps_can_report_a_setup_error():
    def step(run):
        return ci_local.Step(job="j", name="n", run=run, workdir=".")
    assert ci_local.is_setup_exit(step("./rz build --all"), 3)
    assert ci_local.is_setup_exit(step("bash projects/harland/boot/test.sh"), 3)
    assert not ci_local.is_setup_exit(step("python -m pytest -q | tee r.txt"), 3)
    assert not ci_local.is_setup_exit(step("set -e\npytest tools/"), 3)
    assert not ci_local.is_setup_exit(step("./rz build --all"), 1)


@pytest.mark.integration
def test_real_ritz0_pytest_step_cannot_report_a_setup_error():
    """The gate's pytest step and its likely-first pre-pass must read exit 3
    as a crash; build-all's `rz build --all` keeps build.py's meaning."""
    steps = ci_local.load_steps()
    ritz0 = next(s for s in steps if s.name == ci_local.PYTEST_STEP)
    assert not ci_local.is_setup_exit(ritz0, 3)
    _, rest = ci_local.plan_likely_first([ritz0], [])
    if rest is not None:
        assert not ci_local.is_setup_exit(rest, 3)
    build = next(s for s in steps if s.job == "build-all" and s.run.strip() == "./rz build --all")
    assert ci_local.is_setup_exit(build, 3)


def test_real_build_all_wrk_install_is_a_setup_step():
    """AGAST #2464: CI apt-installs wrk for smoke_stack's stack.wrk_index.
    That is runner setup: ci-local must skip it, not run sudo apt-get."""
    steps = [s for s in ci_local.load_steps() if s.job == "build-all" and "wrk" in s.run]
    assert steps and all(s.is_setup for s in steps)


def test_real_build_all_job_is_rz_build_all_then_the_e2e():
    """run-gate.sh relies on build-all's SETUP ERROR (exit 3) coming only
    from `rz build --all`. The other steps are the valet/zeus/nexus e2e
    (AGAST #2107), the valet HTTPS socket test (#2190), the plain-HTTP
    split-request (#2201), short-send (#3678), framing (#1865), large-echo
    (#3900), static-connection (#3899) and command-line (#1495) tests, and the stack smoke
    gate (#2456), which exit 0 or 1 and never 3 -- test_ci_e2e.py holds them
    to that. The harland boot (#1845) exits 3 too, and only for the same
    reason: a missing tool (QEMU, OVMF, GRUB-EFI, or rz build's own exit 3)
    -- test_ci_harland_boot.py holds it to that. So does test-uefi-boot's
    boot/test.sh (#2200; test_harland_uefi_boot_script.py), and the MSI-X
    boot (#1852; test_ci_msix_boot.py) and the NVMe boot (#1850;
    test_ci_nvme_boot.py). A new step here must make the same promise."""
    steps = [s for s in ci_local.load_steps() if s.job == "build-all" and not s.is_setup]
    assert [s.run.strip().splitlines()[-1] for s in steps] == [
        "./rz build --all",
        "bash projects/nexus/test/e2e_large_page.sh",
        "bash projects/valet/test/test_tls_socket.sh",
        "bash projects/valet/test/test_split_request.sh",
        "bash projects/valet/test/test_short_send.sh",
        "bash projects/valet/test/test_framing.sh",
        "bash projects/valet/test/test_large_echo.sh",
        "bash projects/valet/test/test_static_conn.sh",
        "bash projects/valet/test/test_cli.sh",
        "python3 projects/ritz/tools/smoke_stack",
        'KEEP_WORK="$PWD/projects/harland/build/boot-logs" '
        "bash projects/harland/tools/test_tier1_boot.sh",
        "bash projects/harland/boot/test.sh",
        'KEEP_WORK="$PWD/projects/harland/build/boot-logs" '
        "bash projects/harland/tools/test_msix_boot.sh",
        'KEEP_WORK="$PWD/projects/harland/build/boot-logs" '
        "bash projects/harland/tools/test_nvme_boot.sh",
        'KEEP_WORK="$PWD/projects/harland/build/boot-logs" '
        "bash projects/harland/tools/test_nvme_boot.sh",
    ]


def test_the_ritz0_suite_loads_no_stray_plugins():
    """AGAST #2793: ci-local runs main.yml in the caller's venv.  Its plugins
    (django, anyio, ddtrace, ...) cost each of ~31k ritz0 tests ~2 ms and
    capped the xdist controller near 300 tests/s, so the step names the one
    plugin it uses and loads no other."""
    [step] = [s for s in ci_local.load_steps() if s.name == "ritz0 unit tests"]
    words = step.run.split()
    assert "--disable-plugin-autoload" in words
    assert words[words.index("--disable-plugin-autoload") + 1:][:2] == ["-p", "xdist"]


# --------------------------------------------------------------------------
# AGAST #3456 (LARB review/5 tooling F4): likely failures first.  10 of 18
# red gates failed in "ritz0 unit tests", 550-674 s in, because that step
# starts ~6 minutes into the gate.  ci_local now runs the files
# tools/likely_tests.py picks (with the ritz1 build they need) before the
# first step, --maxfail=1, and the full step --ignore's them: a likely failure
# shows in minutes, and a green gate runs every test once, as before.
# --------------------------------------------------------------------------

LIKELY_WF = """\
jobs:
  build-all:
    steps:
      - name: Early
        run: echo early >> {log}
  bootstrap:
    steps:
      - name: Build ritz1 + ritz1_selfhosted
        run: echo build >> {log}
      - name: ritz0 unit tests
        run: |
          set -o pipefail
          echo "pytest ADDOPTS=[$PYTEST_ADDOPTS] PARTIAL=[${{RITZ_TEST_BUDGET_PARTIAL:-}}] INCLUDE=[${{RITZ_COST_REPORT_INCLUDE:-}}]" >> {log}
          echo "{{\\"run\\": \\"$RITZ_TEST_BUDGET_PARTIAL\\"}}" > pytest-cost.json
          : stands in for pytest --cost-report=pytest-cost.json
          if [ -z "${{RITZ_TEST_BUDGET_PARTIAL:-}}" ] && [ -e {full} ]; then cp {full} pytest-cost.json; fi
          if [ -n "${{RITZ_TEST_BUDGET_PARTIAL:-}}" ] && [ -e {fail} ]; then exit 1; fi
        working-directory: r0
      - name: Late
        run: echo late >> {log}
"""


@pytest.fixture
def likely(tmp_path, monkeypatch):
    """A gate-shaped workflow; every step appends a line to `log`."""
    log, fail = tmp_path / "log", tmp_path / "fail-prepass"
    full = tmp_path / "full-step-cost.json"  # the full step's report, if any
    (tmp_path / "r0").mkdir()
    wf = tmp_path / "main.yml"
    wf.write_text(LIKELY_WF.format(log=log, fail=fail, full=full))
    history = tmp_path / "cost-history.json"
    monkeypatch.setenv("RITZ_TEST_COST_HISTORY", str(history))
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    monkeypatch.setattr(ci_local, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ci_local.likely_tests, "select",
                        lambda root: ["test_a.py", "emitter/test_b.py"])
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)

    class Run:
        def __init__(self):
            self.fail = fail
            self.full = full
            self.history = history

        def lines(self):
            return log.read_text().splitlines() if log.exists() else []

    return Run()


GATE = ["--fail-fast", "--job", "build-all", "--job", "bootstrap"]


@pytest.mark.integration
def test_likely_files_run_first_with_their_build_then_the_rest(likely, capsys):
    assert ci_local.main(GATE) == 0
    first_pytest, rest = [ln for ln in likely.lines() if ln.startswith("pytest")]
    assert [ln.split()[0] for ln in likely.lines()] == [
        "build", "pytest", "early", "pytest", "late"], likely.lines()
    # The pre-pass: only the likely files, stopping at the first failure; its
    # budget check judges files, not the suite.
    # AGAST #3623: the files go in as --only-file, never as file arguments:
    # pytest re-walks the whole directory once per file argument.
    assert ("ADDOPTS=[--maxfail=1 --only-file=test_a.py "
            "--only-file=emitter/test_b.py]") in first_pytest
    assert "PARTIAL=[1]" in first_pytest and "INCLUDE=[]" in first_pytest
    # The full step: everything else, with the pre-pass's cost folded in.
    assert "ADDOPTS=[--ignore=test_a.py --ignore=emitter/test_b.py]" in rest
    assert "PARTIAL=[]" in rest and "INCLUDE=[/" in rest
    out = capsys.readouterr().out
    assert "[ritz0 unit tests (likely failures first)] START" in out
    assert "likely failures first: 2 file(s)" in out


@pytest.mark.integration
def test_the_full_step_folds_in_the_pre_pass_cost_report(likely, monkeypatch):
    seen = {}
    real = ci_local.run_step

    def spy(step, dry_run=False):
        inc = step.env.get("RITZ_COST_REPORT_INCLUDE")
        if inc:
            seen["include"] = Path(inc).read_text()
        return real(step, dry_run=dry_run)

    monkeypatch.setattr(ci_local, "run_step", spy)
    assert ci_local.main(GATE) == 0
    # The pre-pass wrote {"run": "1"}; the full step reads that, not its own.
    assert '"run": "1"' in seen["include"]


@pytest.mark.integration
def test_a_pre_pass_failure_stops_a_fail_fast_gate(likely, capsys):
    likely.fail.touch()
    assert ci_local.main(GATE) == 1
    assert [ln.split()[0] for ln in likely.lines()] == ["build", "pytest"]
    out = capsys.readouterr().out
    assert "ritz0 unit tests (likely failures first) (exit 1)" in out
    not_run = out[out.index("not run"):]
    for name in ("Early", "] ritz0 unit tests\n", "Late"):
        assert name in not_run, not_run


@pytest.mark.integration
def test_without_fail_fast_the_rest_still_runs_without_the_likely_files(likely):
    likely.fail.touch()
    assert ci_local.main(GATE[1:]) == 1
    assert [ln.split()[0] for ln in likely.lines()] == [
        "build", "pytest", "early", "pytest", "late"]
    assert "--ignore=test_a.py" in likely.lines()[3]


@pytest.mark.integration
def test_callers_pytest_addopts_are_kept(likely, monkeypatch):
    monkeypatch.setenv("PYTEST_ADDOPTS", "-x")
    assert ci_local.main(GATE) == 0
    first, rest = [ln for ln in likely.lines() if ln.startswith("pytest")]
    assert "ADDOPTS=[-x --maxfail=1 --only-file=test_a.py" in first
    assert "ADDOPTS=[-x --ignore=test_a.py" in rest


@pytest.mark.integration
@pytest.mark.parametrize("why, argv, select", [
    ("nothing selected", GATE, []),
    ("opted out", GATE + ["--no-likely-first"], ["test_a.py"]),
    ("pytest step skipped", GATE + ["--skip", "ritz0 unit tests"], ["test_a.py"]),
    ("pytest job not selected", ["--fail-fast", "--job", "build-all"], ["test_a.py"]),
])
def test_no_pre_pass(likely, monkeypatch, capsys, why, argv, select):
    monkeypatch.setattr(ci_local.likely_tests, "select", lambda root: select)
    assert ci_local.main(argv) == 0
    out = capsys.readouterr().out
    assert "likely failures first)] START" not in out, why
    for ln in likely.lines():
        assert "--ignore" not in ln and "--maxfail" not in ln, why
    assert len([ln for ln in likely.lines() if ln == "build"]) <= 1, why


@pytest.mark.integration
def test_a_failed_build_stops_a_fail_fast_gate_before_the_pre_pass(likely, tmp_path):
    wf = tmp_path / "main.yml"
    wf.write_text(wf.read_text().replace("run: echo build >> ", "run: exit 5; echo "))
    assert ci_local.main(GATE) == 1
    assert likely.lines() == []


def test_real_workflow_has_the_steps_the_pre_pass_runs():
    names = {s.name for s in ci_local.load_steps() if s.job == "bootstrap"}
    assert ci_local.PYTEST_STEP in names
    assert ci_local.PYTEST_PREREQ in names
    step = next(s for s in ci_local.load_steps() if s.name == ci_local.PYTEST_STEP)
    # The cost report the full step folds the pre-pass's into.
    assert ci_local.cost_report_path(step) == "pytest-cost.json"
    # And the pre-pass's report must reach check_test_budget as partial: the
    # step runs the check itself, so it inherits the env ci_local sets.
    assert "check_test_budget.py" in step.run


@pytest.mark.integration
def test_a_stale_cost_report_is_not_folded_in(likely, tmp_path, monkeypatch):
    """A pre-pass that dies before writing its report must not hand the full
    step an earlier run's report left in the tree."""
    (tmp_path / "r0" / "pytest-cost.json").write_text('{"stale": 1}')
    seen = []
    real = ci_local.run_step

    def spy(step, dry_run=False):
        if step.name.endswith(ci_local.PREPASS_SUFFIX):
            return 0  # ran nothing, wrote nothing
        seen.append(step.env.get("RITZ_COST_REPORT_INCLUDE"))
        return real(step, dry_run=dry_run)

    monkeypatch.setattr(ci_local, "run_step", spy)
    assert ci_local.main(GATE) == 0
    assert set(seen) == {None}


# AGAST #3623: a pre-pass whose costly files come last ends on a tail of
# their slow tests while the other workers idle.  The gate keeps the full
# step's cost report on the host, and the next gate's pre-pass hands out its
# files costliest first.

def _report(files: dict[str, float]) -> str:
    return json.dumps({"wall_s": 1.0, "cpu_s": sum(files.values()), "files": {
        f: {"tests": 1, "cpu_s": c, "wall_s": c} for f, c in files.items()}})


def _prepass_addopts(likely) -> str:
    return next(ln for ln in likely.lines() if ln.startswith("pytest"))


@pytest.mark.integration
def test_the_pre_pass_hands_out_the_costliest_files_first(likely, capsys):
    likely.history.write_text(_report({"test_a.py": 1.0, "emitter/test_b.py": 9.0}))
    assert ci_local.main(GATE) == 0
    assert ("ADDOPTS=[--maxfail=1 --only-file=emitter/test_b.py "
            "--only-file=test_a.py]") in _prepass_addopts(likely)
    assert "costliest first (2 of 2 file(s) costed by" in capsys.readouterr().out


@pytest.mark.integration
@pytest.mark.parametrize("history", [None, "{not json", '{"files": []}'])
def test_without_a_usable_cost_history_the_order_is_the_selections(likely, history):
    if history is not None:
        likely.history.write_text(history)
    assert ci_local.main(GATE) == 0
    assert ("ADDOPTS=[--maxfail=1 --only-file=test_a.py "
            "--only-file=emitter/test_b.py]") in _prepass_addopts(likely)


@pytest.mark.integration
def test_a_gate_keeps_the_full_steps_cost_report_for_the_next(likely):
    likely.full.write_text(_report({"test_a.py": 2.0, "test_c.py": 5.0}))
    assert ci_local.main(GATE) == 0
    assert json.loads(likely.history.read_text()) == json.loads(likely.full.read_text())


@pytest.mark.integration
def test_a_full_step_without_a_fresh_report_keeps_the_last_history(
        likely, tmp_path, monkeypatch):
    """A report not in cost_meter's shape, and one left in the tree by an
    earlier run, both leave the host's last good history alone."""
    likely.history.write_text(_report({"test_a.py": 3.0}))
    before = likely.history.read_text()
    assert ci_local.main(GATE) == 0  # the fake's {"run": ""}: not a report
    assert likely.history.read_text() == before

    stale = tmp_path / "r0" / "pytest-cost.json"
    real = ci_local.run_step

    def full_step_writes_nothing(step, dry_run=False):
        if step.name == ci_local.PYTEST_STEP:
            return 0
        rc = real(step, dry_run=dry_run)
        stale.write_text(_report({"stale.py": 1.0}))  # left before the full step
        return rc

    monkeypatch.setattr(ci_local, "run_step", full_step_writes_nothing)
    assert ci_local.main(GATE) == 0
    assert likely.history.read_text() == before


# --------------------------------------------------------------------------
# AGAST #4027 (Aaron 2026-11-18): a gate that knows its base skips "ritz0 unit
# tests" when tools/ritz0_scope.py finds no change that can reach it.  Never
# silently: the SKIPPED line names the inputs and the base.  No --diff-base
# (CI on main) runs everything, and the decision itself is ritz0_scope's
# (tools/test_ritz0_scope.py); these pin how ci_local acts on it.
# --------------------------------------------------------------------------


@pytest.fixture
def scope(likely, monkeypatch):
    """The likely-first gate workflow, with ritz0_scope's verdict stubbed."""
    calls = []

    def set_verdict(skip: bool):
        def fake(repo, base):
            calls.append(base)
            head = (f"SKIPPED ritz0 unit tests: no change under X (base {base[:7]})"
                    if skip else f"running ritz0 unit tests: Y may reach it (base {base[:7]})")
            return ci_local.ritz0_scope.Decision(skip, [head, "  detail"])
        monkeypatch.setattr(ci_local.ritz0_scope, "decide", fake)

    likely.set_verdict = set_verdict
    likely.calls = calls
    return likely


BASE = "abcdef1234567890abcdef1234567890abcdef12"


@pytest.mark.integration
def test_a_scoped_skip_runs_neither_the_step_nor_its_pre_pass(scope, capsys):
    scope.set_verdict(True)
    assert ci_local.main(GATE + ["--diff-base", BASE]) == 0
    assert scope.calls == [BASE]
    # The ritz1 build still runs: later steps need it.
    assert [ln.split()[0] for ln in scope.lines()] == ["early", "build", "late"]
    out = capsys.readouterr().out
    assert "SKIPPED ritz0 unit tests: no change under X (base abcdef1)" in out
    assert "  detail" in out
    assert "likely failures first)] START" not in out
    summary = out[out.index("step timings:"):]
    assert "skipped (no change since --diff-base can reach it" in summary
    assert "[bootstrap] ritz0 unit tests" in summary


@pytest.mark.integration
def test_a_scoped_run_runs_the_step_and_says_why(scope, capsys):
    scope.set_verdict(False)
    assert ci_local.main(GATE + ["--diff-base", BASE]) == 0
    assert [ln.split()[0] for ln in scope.lines()] == [
        "build", "pytest", "early", "pytest", "late"]
    out = capsys.readouterr().out
    assert "running ritz0 unit tests: Y may reach it (base abcdef1)" in out


@pytest.mark.integration
def test_without_a_diff_base_nothing_is_scoped(scope, capsys):
    scope.set_verdict(True)
    assert ci_local.main(GATE) == 0
    assert scope.calls == []
    assert [ln.split()[0] for ln in scope.lines()] == [
        "build", "pytest", "early", "pytest", "late"]
    assert "SKIPPED ritz0 unit tests" not in capsys.readouterr().out


@pytest.mark.integration
@pytest.mark.parametrize("argv", [
    GATE + ["--skip", "ritz0 unit tests"],
    ["--fail-fast", "--job", "build-all"],
])
def test_no_scope_check_when_the_step_would_not_run(scope, argv):
    scope.set_verdict(True)
    assert ci_local.main(argv + ["--diff-base", BASE]) == 0
    assert scope.calls == []


@pytest.mark.integration
def test_a_real_scope_decision_on_a_real_repo(likely, tmp_path, capsys):
    """End to end through git: a docs-only change skips; a ritz0 change runs."""
    import subprocess

    def git(*a):
        return subprocess.run(["git", "-C", str(tmp_path), *a], check=True,
                              capture_output=True, text=True).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "projects/ritz/ritz0").mkdir(parents=True)
    (tmp_path / "projects/ritz/ritz0/parser.py").write_text("x = 1\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/guide.md").write_text("# a\n")
    (tmp_path / ".gitignore").write_text("log\nfail-prepass\nmain.yml\nr0/\n")
    git("add", "-A")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "docs/guide.md").write_text("# b\n")
    git("commit", "-qam", "docs")
    assert ci_local.main(GATE + ["--diff-base", base]) == 0
    assert "pytest" not in [ln.split()[0] for ln in likely.lines()]
    assert "SKIPPED ritz0 unit tests: no change under " in capsys.readouterr().out
    (tmp_path / "log").unlink()
    (tmp_path / "projects/ritz/ritz0/parser.py").write_text("x = 2\n")
    git("commit", "-qam", "ritz0")
    assert ci_local.main(GATE + ["--diff-base", base]) == 0
    assert "pytest" in [ln.split()[0] for ln in likely.lines()]
    assert "projects/ritz/ritz0/parser.py (M) may reach it" in capsys.readouterr().out


def test_gate_runner_passes_its_base():
    """run-gate.sh hands ci_local the base: RZ_GATE_BASE (a train's BASE),
    else the room's merge-base with origin/main.  train.sh passes its BASE on
    both the local and the remote gate."""
    root = ci_local.REPO_ROOT / ".claude/skills/rz-iterate"
    gate, train = root / "run-gate.sh", root / "train.sh"
    if not gate.is_file() or not train.is_file():
        pytest.skip("run-gate.sh is not part of this checkout")
    text = gate.read_text()
    cmd_line = next(line for line in text.splitlines() if line.startswith("CMD="))
    assert "--diff-base $BASE" in cmd_line, cmd_line
    assert "merge-base origin/main" in text
    assert "RZ_GATE_BASE" in text
    calls = [ln for ln in train.read_text().splitlines()
             if "RZ_GATE_TRAIN=1" in ln and not ln.lstrip().startswith("#")]
    assert len(calls) == 2, calls
    for ln in calls:
        assert "RZ_GATE_BASE=" in ln, ln
