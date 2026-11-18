#!/usr/bin/env python3
"""ci_local.py -- run exactly what .github/workflows/main.yml runs, locally.

AGAST #1363.

The problem this solves is not "typing six commands is tedious". It is that a
remembered list of gate commands drifts from CI, and every drift is a green
tick asserting less than you think:

  * `./regression.sh` instead of `scripts/regression.sh` exits 127 -- the shell
    saying the file does not exist -- which reads like a test suite complaining
    about something pre-existing. Caught only because 127 is a wrong-looking
    number for a test suite.
  * `make -C projects/ritz ...` from inside projects/ritz/ritz0 exits 2 for the
    same reason. Hit twice in one session.
  * Steps declare a `working-directory` AFTER their `run:` block, so reading
    the YAML with `grep -A 6` misses it and invites a confident wrong claim
    about what CI actually executes (see #1363's own retraction).

So this does NOT restate the commands. It PARSES main.yml and executes the
`run:` steps it finds, in declaration order, in each step's declared
`working-directory`. A step added to CI is picked up here with no edit; a
command edited in CI changes here too. There is no second list to rot.

Usage
-----

    python3 tools/ci_local.py --list              # what CI declares
    python3 tools/ci_local.py                     # run the `bootstrap` job
    python3 tools/ci_local.py --job build-all
    python3 tools/ci_local.py --job build-all --job test-all --job bootstrap
                                                  # the room gate
    python3 tools/ci_local.py --jobs              # every job

`bootstrap` is the default because it is the compiler gate -- doc examples,
tools tests, harness self-tests, ritz0 unit tests, the bootstrap chain, the
regression matrix and the differential corpus. It is the job a compiler change
must not break.

Environment-setup steps are skipped by default: they are the runner's job, and
running them locally would rewrite the developer's machine or venv. Python,
the toolchain and the pip installs live in the .github/actions/setup action,
a `uses:` step, so they never run here; the `run:` steps named "Install test
tools ..." are skipped unless `--with-setup` is given. Skipped steps are PRINTED, not silently
dropped -- a runner that quietly omits work is the thing this file exists to
prevent.

Skipping setup must not skip its EFFECT on the environment (AGAST #1907).
Each step runs with the workflow/job/step `env:` CI gives it (RITZ_VERIFY_IR=1),
and, after the .github/actions/setup step, with /usr/lib/llvm-$CLANG_VERSION/bin
prepended to PATH as that action does -- without it `opt`/`llvm-as` are absent,
verifier tests skip, and the gate passes what CI fails. A missing bindir fails
the step rather than running on with whatever toolchain happens to be there.

Every step prints `[<step>] START <iso>` and `[<step>] END <iso> <secs>s rc=<n>`,
and the run ends with a timing table (AGAST #1802): before this, every gate
baseline had to be reconstructed from log timestamps.

`--fail-fast` stops at the first failing step and names the steps it did not
run. The gate runner (`run-gate.sh`) turns it on, so a broken ritz1 costs
minutes rather than the whole gate. Without it every step runs, matching CI's
per-step reporting.

`--skip <step name>` (repeatable, exact name) leaves a step out; the gate
runner skips "Smoke" because it has just run `make smoke` itself (AGAST #1897).
A name that matches no step in the selected job(s) exits 2 before anything
runs, so a renamed step cannot quietly turn the skip into a no-op. Skipped
steps are listed in the summary.

`--job` is repeatable; the selected jobs run in workflow order. The gate runner
runs `--job build-all --job test-all --job bootstrap`. Bootstrap alone is the
compiler gate, but a compiler change can break an ecosystem package -- #2124
broke angelo, gated green, and turned main's build-all red for nine runs
(AGAST #2141). test-all (`./rz test --all`, one `PKG <VERDICT> <id>` line per
package) followed for the same reason: a package test break showed up only in
CI after the push to main (AGAST #3969).

Likely failures first (AGAST #3456, LARB review/5 tooling F4). The ritz0
pytest step starts ~6 minutes into a gate, so the 10 of 18 red gates that
failed there reported 550-674 s in. When the selected jobs include that step,
ci_local first runs the step it needs ("Build ritz1 + ritz1_selfhosted"), then
the pytest step's own command on the files tools/likely_tests.py picks (the
test files the last commits changed), with --maxfail=1, as the step "ritz0
unit tests (likely failures first)". The full step then --ignore's those
files, so a green gate runs every test once. Both go through PYTEST_ADDOPTS,
so the command and its flags stay main.yml's. The pre-pass's cost report is
checked per file only (RITZ_TEST_BUDGET_PARTIAL) and folded into the full
step's (RITZ_COST_REPORT_INCLUDE), which is checked whole. `--no-likely-first`
runs the steps exactly as declared.

Diff-scoped ritz0 tests (AGAST #4027, Aaron 2026-11-18). `--diff-base <rev>`
asks tools/ritz0_scope.py whether anything changed since <rev> can reach the
"ritz0 unit tests" step, the longest in every gate. If nothing can (docs, .claude,
...: an allowlist; unknown means run), the step and its likely-first pre-pass
are skipped with `SKIPPED ritz0 unit tests: no change under <inputs> (base
<sha7>)` and listed in the summary; otherwise the line says which path may
reach it. The gate runner passes its base (a room's merge-base with origin/main,
a train's BASE). No --diff-base, as on CI, runs everything.

Exit code: 0 only if every step it ran exited 0. A step that exits 3
(EXIT_SETUP: `rz build --all` saying a toolchain binary is missing, e.g.
lld-link, or the harland boot missing QEMU/OVMF/GRUB-EFI, AGAST #1845)
is a SETUP ERROR -- unless the step runs pytest, whose 3 is INTERNALERROR
(a crashed session) and counts as a failure (AGAST #3624). A SETUP ERROR
does not trip --fail-fast, and if every failure was one the run exits 3 -- not 0 (nothing was verified) and not 1 (nothing
regressed). Any other failure exits 1.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import likely_tests
import ritz0_scope

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"

# Steps that configure the runner rather than test the code. Matched on the
# step's `name`, case-insensitively, as a substring.
SETUP_STEP_MARKERS = ("install toolchain", "install ritz0 dependencies", "install test tools")

DEFAULT_JOB = "bootstrap"

# A step's exit code for "a toolchain binary is missing" -- rz's and
# build.py's EXIT_SETUP (AGAST #2141).
EXIT_SETUP = 3

# pytest exits 3 too, for INTERNALERROR (a conftest or plugin crash), and a
# step that runs it directly (`pytest ... | tee` under pipefail) passes that
# straight through. Such a step's 3 is a crash, never a missing tool
# (AGAST #3624). Matched on the command text, comments included: a false
# match only makes a setup error count as a failure, the safe direction.
# `make` steps need no rule: make turns a recipe's 3 into its own 2.
PYTEST_COMMAND = re.compile(r"\bpytest\b")

# The composite setup action, which pins clang (AGAST #1308; one action for
# every job since #1838). It is a `uses:` step, so it has no command to run --
# but its effect matters: it prepends the versioned LLVM bindir to PATH, which
# is what puts `opt`/`llvm-as` there. Steps after it in the same job get that
# PATH here too (AGAST #1907). Matched exactly: `actions/setup-python@v5`
# contains "actions/setup" too.
TOOLCHAIN_ACTION = "./.github/actions/setup"
LLVM_BINDIR = "/usr/lib/llvm-{version}/bin"

# AGAST #3456: the step whose likely-failing files run first, the step that
# builds what they need, and the name the pre-pass reports under.
PYTEST_STEP = "ritz0 unit tests"
PYTEST_PREREQ = "Build ritz1 + ritz1_selfhosted"
PREPASS_SUFFIX = " (likely failures first)"
_COST_REPORT = re.compile(r"--cost-report=(\S+)")

_EXPR = re.compile(r"\$\{\{\s*env\.(\w+)\s*\}\}")


class Step:
    def __init__(self, job: str, name: str, run: str, workdir: str,
                 env: dict[str, str] | None = None,
                 llvm_bindir: str | None = None):
        self.job = job
        self.name = name
        self.run = run
        self.workdir = workdir
        # workflow < job < step `env:`, merged as Actions merges them.
        self.env = dict(env or {})
        # The pinned toolchain's bindir, if the setup action ran
        # earlier in this job; prepended to PATH when the step runs.
        self.llvm_bindir = llvm_bindir

    @property
    def is_setup(self) -> bool:
        low = self.name.lower()
        return any(m in low for m in SETUP_STEP_MARKERS)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Step({self.job}/{self.name!r} in {self.workdir})"


def load_steps(workflow: Path | None = None) -> list[Step]:
    """Every `run:` step in the workflow, in job then declaration order.

    Steps that use an action (`uses:`) have no shell command and are skipped --
    checkout and setup-python are the runner's concern, not a gate.

    `workflow` defaults to None rather than to WORKFLOW: a default argument is
    bound at definition time, so `workflow=WORKFLOW` would freeze the module
    global and quietly ignore any later override. Resolving it here keeps the
    module honest and keeps the self-tests able to point it at a fixture.
    """
    workflow = workflow or WORKFLOW
    spec = yaml.safe_load(workflow.read_text())
    wf_env = _env_block(spec)
    steps: list[Step] = []
    for job, jobspec in spec.get("jobs", {}).items():
        job_env = {**wf_env, **_env_block(jobspec)}
        bindir = None
        for s in jobspec.get("steps", []) or []:
            if str(s.get("uses", "")).rstrip("/") == TOOLCHAIN_ACTION:
                version = _expand(str((s.get("with") or {}).get("clang-version", "")),
                                  job_env)
                bindir = LLVM_BINDIR.format(version=version)
                continue
            if "run" not in s:
                continue
            steps.append(Step(
                job=job,
                name=s.get("name", "<unnamed>"),
                run=s["run"],
                # A step's working-directory can appear either before or after
                # its `run:` block. Parsing the YAML rather than grepping is
                # exactly why that no longer matters.
                workdir=s.get("working-directory", "."),
                env={**job_env, **_env_block(s)},
                llvm_bindir=bindir,
            ))
    return steps


def _env_block(node: dict) -> dict[str, str]:
    return {str(k): str(v) for k, v in (node.get("env") or {}).items()}


def _expand(value: str, env: dict[str, str]) -> str:
    """Resolve `${{ env.X }}` -- the only expression the workflow feeds the action."""
    return _EXPR.sub(lambda m: env.get(m.group(1), ""), value)


def jobs_in(steps: list[Step]) -> list[str]:
    seen: list[str] = []
    for s in steps:
        if s.job not in seen:
            seen.append(s.job)
    return seen


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def timed_step(step: Step, dry_run: bool = False) -> tuple[int, float]:
    """Run one step between START/END lines; return (rc, seconds)."""
    print(f"[{step.name}] START {_now()}", flush=True)
    t0 = time.monotonic()
    rc = run_step(step, dry_run=dry_run)
    secs = time.monotonic() - t0
    print(f"[{step.name}] END {_now()} {secs:.1f}s rc={rc}", flush=True)
    return rc, secs


def print_timings(timings: list[tuple[str, float, int]]) -> None:
    if not timings:
        return
    width = max(len(n) for n, _, _ in timings)
    print("step timings:")
    for name, secs, rc in timings:
        print(f"  {name:<{width}}  {secs:8.1f}s  rc={rc}")
    total = sum(secs for _, secs, _ in timings)
    print(f"  {'total':<{width}}  {total:8.1f}s")


def _cas_module():
    """projects/ritz/cas.py, loaded by path (it is not an installed package)."""
    spec = importlib.util.spec_from_file_location(
        "ritz_cas", Path(__file__).resolve().parents[1] / "cas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def print_cas_summary(log: Path) -> None:
    """AGAST #1808: one line proving how often the gate compiled each module.

    Every build.py / test_runner process appends its artifact-store counters
    to RITZ_CAS_STATS_LOG; a module named under "compiled more than once" was
    compiled by two processes that missed on the same key at the same time.
    """
    if not log.is_file():
        print("[ritz-cas] gate: no artifact-store activity recorded")
        return
    cas = _cas_module()
    print("\n".join(cas.format_summary(cas.summarise(log))))


def trim_cas() -> None:
    """AGAST #1894: the periodic trim. Every gate ends by bounding the shared
    store to $RITZ_CACHE_MAX_BYTES (default cas.DEFAULT_GC_BYTES), least
    recently used first, so it cannot grow without limit on a machine that
    runs gates all day. Entries this gate used were just touched, so they
    are the last to go."""
    cas = _cas_module()
    store = cas.ArtifactStore()
    removed, freed = store.gc(cas.default_max_bytes())
    print(f"[ritz-cas] gc: removed {removed} files, freed {freed} bytes from {store.root}")


def cost_report_path(step: Step) -> str | None:
    """The `--cost-report=PATH` the step's pytest writes, relative to its cwd."""
    m = _COST_REPORT.search(step.run)
    return m.group(1) if m else None


def _with_addopts(step: Step, name: str, extra: list[str], env: dict[str, str]) -> Step:
    """`step` under another name, with `extra` appended to PYTEST_ADDOPTS."""
    opts = " ".join(x for x in (os.environ.get("PYTEST_ADDOPTS", ""),
                                step.env.get("PYTEST_ADDOPTS", ""), shlex.join(extra)) if x)
    return Step(job=step.job, name=name, run=step.run, workdir=step.workdir,
                env={**step.env, **env, "PYTEST_ADDOPTS": opts},
                llvm_bindir=step.llvm_bindir)


def plan_likely_first(steps: list[Step], skip: list[str]) -> tuple[list[Step], Step | None]:
    """(steps to run before the first step, the full pytest step to rewrite).

    Empty when the pytest step is not selected or skipped, or nothing is
    likely: then every step runs as declared.
    """
    pytest_step = next((s for s in steps if s.name == PYTEST_STEP), None)
    if pytest_step is None or PYTEST_STEP in skip:
        return [], None
    files = likely_tests.select(REPO_ROOT)
    if not files:
        print("likely failures first: no recently changed ritz0 test files")
        return [], None
    print(f"likely failures first: {len(files)} file(s) from tools/likely_tests.py, "
          f"then the rest of {PYTEST_STEP!r} without them:")
    for f in files:
        print(f"  {f}")
    early = [s for s in steps if s.name == PYTEST_PREREQ and s.name not in skip]
    early.append(_with_addopts(pytest_step, PYTEST_STEP + PREPASS_SUFFIX,
                               ["--maxfail=1", *files],
                               {"RITZ_TEST_BUDGET_PARTIAL": "1"}))
    rest = _with_addopts(pytest_step, PYTEST_STEP,
                         [f"--ignore={f}" for f in files], {})
    return early, rest


def run_step(step: Step, dry_run: bool = False) -> int:
    cwd = (REPO_ROOT / step.workdir).resolve()
    print(f"\n{'=' * 70}", flush=True)
    print(f"[{step.job}] {step.name}", flush=True)
    print(f"  cwd: {cwd}", flush=True)
    print(f"{'=' * 70}", flush=True)
    if step.llvm_bindir:
        print(f"  PATH: {step.llvm_bindir} prepended (.github/actions/setup)", flush=True)
    for k, v in step.env.items():
        print(f"  env: {k}={v}", flush=True)
    if dry_run:
        for line in step.run.rstrip().split("\n"):
            print(f"  $ {line}", flush=True)
        return 0
    if not cwd.is_dir():
        # The 127/2 class of failure, named rather than left to a shell.
        print(f"  ERROR: working-directory does not exist: {cwd}", file=sys.stderr)
        return 2
    env = {**os.environ, **step.env}
    if step.llvm_bindir:
        if not Path(step.llvm_bindir).is_dir():
            # CI's action fails here too. Running on without it would skip
            # every verifier-dependent test: the #1907 miss.
            print(f"  ERROR: pinned LLVM toolchain not installed: {step.llvm_bindir} "
                  f"(see projects/ritz/docs/TOOLCHAIN.md)", file=sys.stderr)
            return 2
        env["PATH"] = step.llvm_bindir + os.pathsep + env.get("PATH", "")
    return subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step.run],
                          cwd=cwd, env=env).returncode


def is_setup_exit(step: Step, rc: int) -> bool:
    """Whether `rc` is build.py's "a toolchain binary is missing" (EXIT_SETUP)
    rather than a failure. Not for a step that runs pytest, whose 3 is
    INTERNALERROR (see PYTEST_COMMAND)."""
    return rc == EXIT_SETUP and not PYTEST_COMMAND.search(step.run)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--job", action="append", default=[],
                   help=f"run this job (repeatable; default: {DEFAULT_JOB})")
    p.add_argument("--jobs", action="store_true", help="run every job")
    p.add_argument("--list", action="store_true",
                   help="print the steps CI declares and exit")
    p.add_argument("--dry-run", action="store_true",
                   help="print each command instead of running it")
    p.add_argument("--with-setup", action="store_true",
                   help="also run toolchain/dependency install steps")
    p.add_argument("--fail-fast", action="store_true",
                   help="stop at the first failing step (the gate's default)")
    p.add_argument("--no-likely-first", action="store_true",
                   help="do not run the likely-failing ritz0 test files first "
                        "(AGAST #3456); run every step as declared")
    p.add_argument("--diff-base", metavar="REV",
                   help=f"skip {PYTEST_STEP!r} if no change since REV can reach it "
                        "(tools/ritz0_scope.py; AGAST #4027)")
    p.add_argument("--skip", action="append", default=[], metavar="STEP",
                   help="do not run the step with this exact name (repeatable); "
                        "an unknown name is an error")
    args = p.parse_args(argv)

    if not WORKFLOW.is_file():
        print(f"workflow not found: {WORKFLOW}", file=sys.stderr)
        return 2

    steps = load_steps()
    available = jobs_in(steps)

    if args.list:
        for job in available:
            print(f"--- {job} ---")
            for s in (x for x in steps if x.job == job):
                tag = "  (setup)" if s.is_setup else ""
                print(f"   [{s.workdir}] {s.name}{tag}")
        return 0

    if args.jobs:
        selected = available
    else:
        wanted = args.job or [DEFAULT_JOB]
        bad = [j for j in wanted if j not in available]
        if bad:
            print(f"unknown job {', '.join(repr(j) for j in bad)}; "
                  f"available: {', '.join(available)}", file=sys.stderr)
            return 2
        # Workflow order, not argv order: the same run whichever way it's typed.
        selected = [j for j in available if j in wanted]

    # A --skip that matches nothing would be a silent no-op the day the step
    # is renamed, and the gate would quietly pay for it again (AGAST #1897).
    known = [s.name for s in steps if s.job in selected]
    unknown = [n for n in args.skip if n not in known]
    if unknown:
        print(f"--skip names no step in {', '.join(selected)}: "
              f"{', '.join(repr(n) for n in unknown)}; steps: "
              f"{', '.join(repr(n) for n in known)}", file=sys.stderr)
        return 2

    cas_log = None
    if not args.dry_run and not os.environ.get("RITZ_CAS_STATS_LOG"):
        fd, name = tempfile.mkstemp(prefix="ritz-cas-stats-", suffix=".jsonl")
        os.close(fd)
        cas_log = Path(name)
        os.environ["RITZ_CAS_STATS_LOG"] = name  # inherited by every step

    failures: list[str] = []
    setup_errors: list[str] = []
    skipped: list[str] = []
    not_run: list[str] = []
    skipped_by_request: list[str] = []
    timings: list[tuple[str, float, int]] = []

    def run(s: Step) -> None:
        if failures and args.fail_fast:
            not_run.append(f"[{s.job}] {s.name}")
            return
        rc, secs = timed_step(s, dry_run=args.dry_run)
        timings.append((s.name, secs, rc))
        if is_setup_exit(s, rc):
            # The machine's fault: no verdict on the code, so no fail-fast.
            setup_errors.append(f"[{s.job}] {s.name} (exit {rc})")
        elif rc != 0:
            failures.append(f"[{s.job}] {s.name} (exit {rc})")

    chosen = [s for s in steps if s.job in selected]
    # AGAST #4027: a gate that knows its base may leave the ritz0 step out.
    # Only asked when the step would otherwise run; any doubt means run.
    scoped_out: list[str] = []
    if args.diff_base and PYTEST_STEP not in args.skip and \
            any(s.name == PYTEST_STEP for s in chosen):
        decision = ritz0_scope.decide(REPO_ROOT, args.diff_base)
        print("\n".join(decision.lines), flush=True)
        if decision.skip:
            scoped_out = [s.name for s in chosen if s.name == PYTEST_STEP]
    plan_skip = args.skip + scoped_out
    early, rest = ([], None) if args.no_likely_first else \
        plan_likely_first(chosen, plan_skip)
    ran_early = {s.name for s in early}
    include_dir = tempfile.mkdtemp(prefix="ritz-likely-first-") if early else None
    for s in early:
        report = cost_report_path(s)
        prepass = s.name.endswith(PREPASS_SUFFIX) and report and not args.dry_run
        src = (REPO_ROOT / s.workdir / report).resolve() if prepass else None
        if src is not None:
            # An earlier run's report must not pass for this one's.
            src.unlink(missing_ok=True)
        run(s)
        if src is not None and src.is_file():
            # Moved aside, so the full step's report folds it in rather than
            # overwriting it.
            dst = Path(include_dir) / "prepass-cost.json"
            shutil.move(src, dst)
            rest.env["RITZ_COST_REPORT_INCLUDE"] = str(dst)

    skipped_by_scope: list[str] = []
    for s in chosen:
        if s.name in scoped_out:
            skipped_by_scope.append(f"[{s.job}] {s.name}")
            continue
        if s.name in args.skip:
            skipped_by_request.append(f"[{s.job}] {s.name}")
            continue
        if s.is_setup and not args.with_setup:
            skipped.append(f"[{s.job}] {s.name}")
            continue
        if s.name in ran_early:
            continue
        run(rest if rest is not None and s.name == PYTEST_STEP else s)
    if include_dir:
        shutil.rmtree(include_dir, ignore_errors=True)

    print(f"\n{'=' * 70}")
    print_timings(timings)
    if cas_log is not None:
        print_cas_summary(cas_log)
        cas_log.unlink(missing_ok=True)
        trim_cas()
    if not_run:
        # Named, never silent: a fail-fast run asserts less than a full one.
        print("not run (--fail-fast stopped after the first failure):")
        for s in not_run:
            print(f"  - {s}")
    if skipped_by_request:
        # A gate that skipped a step asserts less than CI; say which.
        print("skipped (--skip):")
        for s in skipped_by_request:
            print(f"  - {s}")
    if skipped_by_scope:
        # A gate that skipped a step asserts less than CI; say which, and why.
        print(f"skipped (no change since --diff-base can reach it; "
              f"tools/ritz0_scope.py, AGAST #4027):")
        for s in skipped_by_scope:
            print(f"  - {s}")
    if skipped:
        # Printed, never silent: see the module docstring.
        print("skipped (environment setup; --with-setup to include):")
        for s in skipped:
            print(f"  - {s}")
    if setup_errors:
        print(f"⚠ SETUP ERROR in {len(setup_errors)} step(s) -- a missing tool, "
              f"not a regression; not verified on this machine:")
        for f in setup_errors:
            print(f"  - {f}")
    if failures:
        print(f"✗ {len(failures)} step(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    if setup_errors:
        return EXIT_SETUP
    print(f"✓ all steps passed for: {', '.join(selected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
