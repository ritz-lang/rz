"""Running a package's tests: `build.py test` and `rz test`'s units.

Split out of build.py (AGAST #3632): test-file discovery, one file's run
(in-process or as a `ritz0 --test` child) and its verdict, the Σ line, and
the `--unit-plan` / `--unit-file` entry points `rz test --all -j N`
schedules. build.py re-exports all of it.
"""

import os
import re
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import bounded_run
from build_pipeline import (RITZ0, build_package, relay_compiler_warnings,
                            test_env_for_files)
from manifest import discover_test_files


_HARNESS_SUMMARY = re.compile(r"(\d+) passed, (\d+) failed(?:, (\d+) errored)?")


def failure_lines(stdout: str) -> list[str]:
    """The "Failures:" block of a `ritz0 --test` report, one line each.

    test_runner.run_files ends its report with "Failures:" and one
    "  - <test fn>: exited with code N" (or "crashed with signal S",
    "timeout") per failed test, its output indented under it. build.py
    echoed only lines containing "FAIL" or "assertion", which none of those
    contain, so a gate log said "7 passed, 1 failed" and never which test
    or why (AGAST #4052). Lines lose the report's two-space indent.
    """
    lines: list[str] = []
    in_block = False
    for line in stdout.splitlines():
        if line == "Failures:":
            in_block, lines = True, []  # the last block wins
        elif in_block and line.startswith("  "):
            lines.append(line[2:])
        elif in_block:
            in_block = False
    return lines


def classify_test_file(returncode: int, stdout: str) -> tuple[str, int, int]:
    """Classify one `ritz0 --test <file>` run as (status, passed, failed).

    status is one of:
      pass   exited 0, printed a harness summary, at least one test ran, none failed
      fail   the harness ran and at least one test failed
      error  non-zero exit, no harness summary, or "K errored": a file
             that did not compile or link (AGAST #3795), or a crash
      empty  exited 0 and ran ZERO tests

    `empty` is a failure, not a pass (AGAST #1345). `ritz0 --test` prints
    "0 passed, 0 failed" and exits 0 for a file with no [[test]] function,
    and this used to be reported as "✓ file — 0 passed". A test file that
    cannot fail cannot be told apart from one that does not exist.
    """
    passed = failed = errored = 0
    seen = False
    for line in stdout.splitlines():
        m = _HARNESS_SUMMARY.search(line)
        if m:  # last matching line wins
            passed, failed = int(m.group(1)), int(m.group(2))
            errored = int(m.group(3) or 0)
            seen = True
    # A file that did not build ran no test: not an assertion failure.
    if errored > 0:
        return "error", passed, failed
    # Checked BEFORE the exit code: `ritz0 --test` exits 1 when a test fails.
    # The old inline parser tested `returncode != 0` first, so every
    # assertion failure was reported as a compile failure and the Σ line's
    # "failed" count could only ever be 0.
    if failed > 0:
        return "fail", passed, failed
    if returncode != 0 or not seen:
        return "error", passed, failed
    if passed == 0:
        return "empty", passed, failed
    return "pass", passed, failed


def format_test_summary(n_files: int, tests_passed: int, tests_failed: int,
                        n_fail: int, n_error: int, n_empty: int,
                        n_timeout: int) -> str:
    """The Σ line for a package's .ritz test files.

    The headline counts FILES that did not pass. It used to read

        Σ 255 passed, 0 failed, 3 compile-failed, 0 timed-out

    and "0 failed" beside three compile failures reads as green to anyone
    scanning a log (AGAST #1345). A file that failed to compile has not
    passed. Zero counts are left out, so nothing prints "0 failed".
    """
    not_passing = n_fail + n_error + n_empty + n_timeout
    if not_passing == 0:
        return f"  Σ ✓ {n_files} of {n_files} files passed ({tests_passed} tests)"
    parts = []
    if n_fail:
        parts.append(f"{n_fail} with failing tests ({tests_failed} failed)")
    if n_error:
        parts.append(f"{n_error} compile-failed")
    if n_empty:
        parts.append(f"{n_empty} with no [[test]] functions")
    if n_timeout:
        parts.append(f"{n_timeout} timed-out")
    ok = n_files - not_passing
    return (f"  Σ ✗ {not_passing} of {n_files} files FAILED: {', '.join(parts)}"
            f" | {ok} file(s) passed, {tests_passed} tests passed")


def per_file_timeout() -> int:
    """Per-file timeout budget. 180s handles even slow elliptic-curve bigint
    tests on a debug build; can be tuned via RITZ_TEST_TIMEOUT."""
    return int(os.environ.get("RITZ_TEST_TIMEOUT", "180"))


@dataclass
class _TestRun:
    """What one `ritz0 --test <file>` printed, and its exit code."""
    returncode: int
    stdout: str
    stderr: str


def _ritz0_test_subprocess(tfile: Path, pkg_dir: Path, test_env: dict,
                           timeout: int, compiler: str) -> Optional[_TestRun]:
    """`ritz0 --test <tfile>` as a child process; None if it timed out."""
    cmd = [sys.executable, str(RITZ0), "--test", str(tfile)]
    if compiler != "ritz0":
        cmd += ["--compiler", compiler]
    try:
        r = subprocess.run(cmd, cwd=pkg_dir, env=test_env, capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    return _TestRun(r.returncode, r.stdout, r.stderr)


_TEST_RUNNER = None

# The build.py module object (set by build.py on import), which stands for
# the whole build system; given to test_runner, which loads build.py itself
# otherwise.
BUILD_MODULE = None


def _test_runner():
    """ritz0/test_runner.py, imported once (RITZ0_DIR is on sys.path)."""
    global _TEST_RUNNER
    if _TEST_RUNNER is None:
        import importlib
        tr = importlib.import_module("test_runner")
        # It loads build.py for the store key and object flags; in this
        # process that is already imported (build.py sets BUILD_MODULE).
        if tr._BUILD_MODULE is None and BUILD_MODULE is not None:
            tr._BUILD_MODULE = BUILD_MODULE
        _TEST_RUNNER = tr
    return _TEST_RUNNER


def _can_run_in_process() -> bool:
    """The in-process timeout is a SIGALRM, which only the main thread gets."""
    return threading.current_thread() is threading.main_thread()


class _TestFileTimeout(BaseException):
    """Raised by SIGALRM. A BaseException, so run_files' per-file `except
    Exception` cannot turn the timeout into an ordinary failure."""


def _ritz0_test_in_process(tfile: Path, pkg_dir: Path, test_env: dict,
                           timeout: int, compiler: str) -> Optional[_TestRun]:
    """What `ritz0 --test <tfile>` would print, without starting it.

    AGAST #1915: the subprocess cost a second interpreter, ritz0.py's imports
    and test_runner's on every file unit, ~0.7 s per file before any work.
    test_runner.run_files is the code `ritz0 --test` runs, so the report (and
    classify_test_file's verdict) is the same. The child ran in pkg_dir with
    test_env (integration tests `fork/exec ./binary`); so does this, and both
    are put back afterwards. None if `timeout` expired: SIGALRM unwinds the
    run, and subprocess.run kills whatever child was running.
    """
    import contextlib
    import io

    tr = _test_runner()
    tfile = tfile.resolve()  # relative to our cwd, not pkg_dir
    out, err = io.StringIO(), io.StringIO()
    old_cwd, old_env = os.getcwd(), os.environ.copy()

    def on_alarm(_signum, _frame):
        raise _TestFileTimeout()

    old_handler = signal.signal(signal.SIGALRM, on_alarm)
    try:
        try:
            signal.setitimer(signal.ITIMER_REAL, timeout)
            os.environ.clear()
            os.environ.update(test_env)
            os.chdir(pkg_dir)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = tr.run_files([str(tfile)], compiler=compiler)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    except _TestFileTimeout:
        return None
    finally:
        signal.signal(signal.SIGALRM, old_handler)
        os.chdir(old_cwd)
        os.environ.clear()
        os.environ.update(old_env)
    return _TestRun(rc, out.getvalue(), err.getvalue())


def run_test_file(tfile: Path, pkg_dir: Path, test_env: dict,
                  timeout: int, compiler: str = "ritz0") -> dict:
    """Run one `ritz0 --test <tfile>` and print its verdict line(s).

    In-process on the main thread (AGAST #1915), as a `ritz0.py --test` child
    otherwise; both run test_runner.run_files and print the same report.

    `compiler` builds the test binary (`--compiler`, AGAST #1908): with a
    ritz1-family compiler, ritz0.py only drives the harness; every object in
    the binary, ritzunit's included, is compiled by `compiler`.

    Returns {"status", "passed", "failed"}, status being one of
    classify_test_file's statuses or "timeout". Shared by the serial loop
    in run_tests and by the `--unit-file` entry point, so a file's verdict
    and its printed lines are identical in both modes.

    Execution CWD matters for integration tests that `fork/exec ./binary`
    (see tier1/01_hello's test_hello_output). We run from pkg_dir so those
    relative paths work; imports still resolve via RITZ_PATH (env-based,
    not CWD-based — see ritz0/import_resolver.py).
    """
    run = _ritz0_test_in_process if _can_run_in_process() else _ritz0_test_subprocess
    result = run(Path(tfile), Path(pkg_dir), test_env, timeout, compiler)
    if result is None:
        print(f"    ⏱  {tfile.name} — TIMEOUT after {timeout}s")
        return {"status": "timeout", "passed": 0, "failed": 0}

    relay_compiler_warnings(result.stderr)
    status, file_passed, file_failed = classify_test_file(
        result.returncode, result.stdout)
    outcome = {"status": status, "passed": file_passed, "failed": file_failed}

    if status == "empty":
        print(f"    ✗ {tfile.name} — ran 0 tests: no [[test]] functions "
              f"(a test file that cannot fail is not a test)")
    elif status == "error":
        # Compile / link / runtime failure before harness summary
        err_first = compile_failure_reason(result.stdout, result.stderr)
        print(f"    ✗ {tfile.name} — {err_first}")
    elif status == "fail":
        # Compiled and ran but some tests failed: name each one and how it
        # failed (AGAST #4052), from the report's "Failures:" block.
        print(f"    ✗ {tfile.name} — {file_passed} passed, {file_failed} failed")
        for line in failure_lines(result.stdout):
            print(f"        {line}")
    else:
        print(f"    ✓ {tfile.name} — {file_passed} passed")
    return outcome


_DID_NOT_BUILD = re.compile(r"^\s*- .*?: did not build: (.+)$")
_HARNESS_SUMMARY_LINE = re.compile(r"^\s*\d+ passed, \d+ failed")
# Long enough for an absolute path plus the message: the harness's reason
# names the file absolutely, and under a gate tree's pytest tmpdir the path
# alone passed the old 200-char cut, dropping the diagnostic (AGAST #2210).
_REASON_MAX = 1000


def _compile_failure_reason(stdout: str, stderr: str) -> str:
    """The most actionable line of a test file that did not build or run.

    In order: the first line on stderr naming an error, case-insensitively,
    so the compiler's "Error in <file>: ..." matches (AGAST #1324, #3795);
    the harness's own `- <file>: did not build: <diagnostic>` line, since
    stderr does not always carry the diagnostic (a ritz1 child writes to
    fd 2 directly, past an in-process redirect) (AGAST #2210); the first
    such line on stdout; the last line. The harness's "0 passed, 0 failed,
    1 errored" summary names no reason and is never taken.
    """
    stdout, stderr = stdout or "", stderr or ""

    def first_error_line(text: str) -> str:
        for line in text.splitlines():
            if _HARNESS_SUMMARY_LINE.match(line):
                continue
            low = line.lower()
            if any(tag in low for tag in (
                "cannot select", "fatal error", "error", "valueerror:",
                "unknown function", "illegal instruction", "segmentation fault",
            )):
                return line.strip()
        return ""

    reason = first_error_line(stderr)
    if reason:
        return reason
    for line in stdout.splitlines():
        m = _DID_NOT_BUILD.match(line)
        if m:
            return m.group(1).strip()
    reason = first_error_line(stdout)
    if reason:
        return reason
    blob = (stderr + stdout).strip()
    return blob.splitlines()[-1] if blob else "(no output)"


def compile_failure_reason(stdout: str, stderr: str) -> str:
    """_compile_failure_reason, cut to _REASON_MAX (one huge line, e.g. an
    IR dump, must not flood the test listing)."""
    return _compile_failure_reason(stdout, stderr)[:_REASON_MAX]


def summarize_file_outcomes(outcomes: list[dict]) -> str:
    """The Σ line for a list of run_test_file outcomes."""
    by = lambda s: sum(1 for o in outcomes if o["status"] == s)  # noqa: E731
    # Assertion counts only from files whose harness summary was trusted,
    # exactly as the serial loop always counted them.
    counted = [o for o in outcomes if o["status"] in ("pass", "fail")]
    return format_test_summary(
        n_files=len(outcomes),
        tests_passed=sum(o["passed"] for o in counted),
        tests_failed=sum(o["failed"] for o in counted),
        n_fail=by("fail"),
        n_error=by("error"),
        n_empty=by("empty"),
        n_timeout=by("timeout"),
    )


def run_test_sh(pkg_dir: Path) -> bool:
    """Run pkg_dir/test.sh (caller checks it exists); print its verdict."""
    print(f"  🧪 Running test.sh...")
    result = bounded_run.child(
        ["bash", str(pkg_dir / "test.sh")],
        cwd=pkg_dir,
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"    ✓ test.sh passed")
        return True
    print(f"  ✗ test.sh failed:")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return False


def run_tests(pkg_dir: Path, config: dict, compiler: str = "ritz0") -> bool:
    """Run tests for a package with `compiler`.

    Every test binary is built by `compiler`: the test file in test mode,
    its dependencies and ritzunit (AGAST #1908). Before that, ritz1 had no
    test mode and its files were reported as NOT run (#1500): a ritz1 run
    must never fall back to ritz0.
    """
    all_passed = True
    tests_found = False

    ritz_tests = discover_test_files(pkg_dir, config)

    if ritz_tests:
        tests_found = True
        print(f"  🧪 Running {len(ritz_tests)} .ritz test file(s)...")
        # ritz0 --test compiles a test-harness binary and then EXECUTES it.
        # We run files ONE AT A TIME rather than passing all files to a single
        # ritz0 invocation: a single shared 5-minute deadline used to be enough
        # to kill the whole suite when any one file (e.g. ed25519, p256) was
        # slow to optimize, AND a single compile-time failure (e.g. an unknown
        # intrinsic) would terminate the batch before later files could run.
        # Per-file invocations cost a bit more on Python startup but give
        # accurate aggregate results and let one bad file fail in isolation.
        # (`rz test --all -j N` runs these same per-file units concurrently
        # across the workspace via --unit-file; AGAST #1809.)
        test_env = test_env_for_files()
        timeout = per_file_timeout()
        outcomes = [run_test_file(t, pkg_dir, test_env, timeout, compiler)
                    for t in ritz_tests]
        if any(o["status"] != "pass" for o in outcomes):
            all_passed = False
        print(summarize_file_outcomes(outcomes))

    # Run test.sh if it exists
    if (pkg_dir / "test.sh").exists():
        tests_found = True
        if not run_test_sh(pkg_dir):
            all_passed = False

    if not tests_found:
        print(f"  ⚠ No tests found, skipping")

    return all_passed


# --- `rz test --all -j N` units (AGAST #1809) ------------------------------
#
# The workspace `rz` schedules a package's test run as independent units on
# one bounded worker pool, so files from different packages (and different
# files of one package) run concurrently:
#
#   --unit-plan PATH     build the package (exactly what `test` builds) and
#                        write the plan: which test files to run, whether
#                        test.sh exists. Exit 0 iff the build succeeded and
#                        the files can be run with this compiler.
#   --unit-file F        run ONE test file (no build); write its outcome to
#                        --unit-result. Exit 0 iff it passed.
#   --unit-test-sh       run test.sh only (no build).
#
# Each unit prints exactly the lines the serial `test` prints for that step
# (same helpers), and `rz` prints the buffered units back in serial order with
# the same Σ line (summarize_file_outcomes), so the verdict and the log read
# the same in both modes. Discovery stays here (discover_test_files); `rz`
# never globs test files itself.


def unit_plan(pkg_dir: Path, config: dict, plan_path: Path, *,
              keep_artifacts: bool, use_cache: bool,
              profile_name: Optional[str], compiler: str) -> int:
    """Build step of a package's test run; writes the plan JSON.

    Mirrors cmd_test's per-package build branch and run_tests' preamble:
    a failed build runs nothing (built=false), and test.sh still runs.
    """
    import json
    pkg_name = config["package"]["name"]
    built = True
    if config.get("build", {}).get("test_only", False):
        print(f"📦 {pkg_name} (test-only)")
    else:
        result = build_package(pkg_dir, config, keep_artifacts=keep_artifacts,
                               use_cache=use_cache, profile_name=profile_name,
                               compiler=compiler)
        if not result.ok:
            print(f"  ✗ Failed to build {pkg_name}: {result.summary()}",
                  file=sys.stderr)
            built = False

    files: list[Path] = []
    if built:
        files = discover_test_files(pkg_dir, config)
    plan = {
        "built": built,
        "files": [str(f) for f in files],
        "test_sh": built and (pkg_dir / "test.sh").exists(),
    }
    plan_path.write_text(json.dumps(plan))
    return 0 if built else 1


def unit_file(pkg_dir: Path, tfile: Path, result_path: Path,
              compiler: str = "ritz0") -> int:
    """Run one test file; write its run_test_file outcome as JSON."""
    import json
    outcome = run_test_file(tfile, pkg_dir, test_env_for_files(),
                            per_file_timeout(), compiler)
    result_path.write_text(json.dumps(outcome))
    return 0 if outcome["status"] == "pass" else 1
