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
    python3 tools/ci_local.py --jobs              # every job (slow: test-all
                                                  # sweeps 26 projects, ~50m)

`bootstrap` is the default because it is the compiler gate -- doc examples,
tools tests, harness self-tests, ritz0 unit tests, the bootstrap chain, the
regression matrix and the differential corpus. It is the job a compiler change
must not break.

Environment-setup steps (toolchain, pip installs) are skipped by default: they
are the runner's job, and running them locally would rewrite the developer's
venv. `--with-setup` includes them. Skipped steps are PRINTED, not silently
dropped -- a runner that quietly omits work is the thing this file exists to
prevent.

Skipping setup must not skip its EFFECT on the environment (AGAST #1907).
Each step runs with the workflow/job/step `env:` CI gives it (RITZ_VERIFY_IR=1),
and, after an install-toolchain step, with /usr/lib/llvm-$CLANG_VERSION/bin
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

Exit code: 0 only if every step it ran exited 0.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import tempfile
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"

# Steps that configure the runner rather than test the code. Matched on the
# step's `name`, case-insensitively, as a substring.
SETUP_STEP_MARKERS = ("install toolchain", "install ritz0 dependencies")

DEFAULT_JOB = "bootstrap"

# The composite action that pins clang (AGAST #1308). It is a `uses:` step, so
# it has no command to run -- but its effect matters: it prepends the
# versioned LLVM bindir to PATH, which is what puts `opt`/`llvm-as` there.
# Steps after it in the same job get that PATH here too (AGAST #1907).
TOOLCHAIN_ACTION = "install-toolchain"
LLVM_BINDIR = "/usr/lib/llvm-{version}/bin"

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
        # The pinned toolchain's bindir, if an install-toolchain step ran
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
            if TOOLCHAIN_ACTION in str(s.get("uses", "")):
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


def run_step(step: Step, dry_run: bool = False) -> int:
    cwd = (REPO_ROOT / step.workdir).resolve()
    print(f"\n{'=' * 70}", flush=True)
    print(f"[{step.job}] {step.name}", flush=True)
    print(f"  cwd: {cwd}", flush=True)
    print(f"{'=' * 70}", flush=True)
    if step.llvm_bindir:
        print(f"  PATH: {step.llvm_bindir} prepended (install-toolchain)", flush=True)
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--job", help=f"run one job (default: {DEFAULT_JOB})")
    p.add_argument("--jobs", action="store_true", help="run every job")
    p.add_argument("--list", action="store_true",
                   help="print the steps CI declares and exit")
    p.add_argument("--dry-run", action="store_true",
                   help="print each command instead of running it")
    p.add_argument("--with-setup", action="store_true",
                   help="also run toolchain/dependency install steps")
    p.add_argument("--fail-fast", action="store_true",
                   help="stop at the first failing step (the gate's default)")
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
        job = args.job or DEFAULT_JOB
        if job not in available:
            print(f"unknown job {job!r}; available: {', '.join(available)}",
                  file=sys.stderr)
            return 2
        selected = [job]

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
    skipped: list[str] = []
    not_run: list[str] = []
    skipped_by_request: list[str] = []
    timings: list[tuple[str, float, int]] = []
    for s in steps:
        if s.job not in selected:
            continue
        if s.name in args.skip:
            skipped_by_request.append(f"[{s.job}] {s.name}")
            continue
        if s.is_setup and not args.with_setup:
            skipped.append(f"[{s.job}] {s.name}")
            continue
        if failures and args.fail_fast:
            not_run.append(f"[{s.job}] {s.name}")
            continue
        rc, secs = timed_step(s, dry_run=args.dry_run)
        timings.append((s.name, secs, rc))
        if rc != 0:
            failures.append(f"[{s.job}] {s.name} (exit {rc})")

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
    if skipped:
        # Printed, never silent: see the module docstring.
        print("skipped (environment setup; --with-setup to include):")
        for s in skipped:
            print(f"  - {s}")
    if failures:
        print(f"✗ {len(failures)} step(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"✓ all steps passed for: {', '.join(selected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
