"""AGAST #1909: ritzunit `-j N` runs a binary's tests in a pool of N children.

Each child has its own capture file; the runner blocks until a child exits or
the earliest deadline passes (no busy poll), and reports in run order, so the
report does not depend on which child finished first. test_ritzunit_harness.py
runs all of its attribution tests under `-j 4` too; these pin what only the
pool has: wall time, the N bound, ordering, fail-fast and timeouts.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(RITZ0_DIR))

import test_ritzunit_harness as harness  # noqa: E402

# The harness's package-writing fixture and binary builder.
package = harness.package
_binary = harness._binary

pytestmark = pytest.mark.integration

# A `[[test]]` that sleeps `ms` then returns `ret`, printing its own name.
SLEEPER = """\
[[test]]
fn {name}() -> i32
    prints("{name} out\\n")
    var req: [2]i64
    req[0] = {sec}
    req[1] = {nsec}
    sys_nanosleep(@req[0], null)
    {ret}

"""

HEADER = "import ritzlib.io\nimport ritzlib.sys\n\n"


def sleepers(*specs) -> str:
    """Source for tests given as (name, ms, ret)."""
    body = "".join(SLEEPER.format(name=n, sec=ms // 1000, nsec=(ms % 1000) * 1000000, ret=r)
                   for n, ms, r in specs)
    return HEADER + body


def run(exe: str, *args: str):
    start = time.monotonic()
    # Short: a runner that misses a deadline hangs on a looping test.
    proc = subprocess.run([exe, *args], capture_output=True, timeout=30)
    return proc, time.monotonic() - start


def test_k_sleepers_take_k_over_n_seconds(package, tmp_path):
    """Acceptance: 6 tests sleeping 1 s take ~2 s with -j 3, ~6 s without."""
    exe = _binary(package(sleepers(*[(f"sleep_{i}", 1000, 0) for i in range(6)])), tmp_path)
    proc, wall = run(exe, "--json", "-j", "3")
    report = json.loads(proc.stdout)
    assert report["summary"]["passed"] == 6, report
    assert proc.returncode == 0
    # At most 3 live at once (>= 2 s) and actually 3 at once (well under 3 s).
    assert 1.9 <= wall < 3.0, wall


def test_jobs_one_is_sequential(package, tmp_path):
    exe = _binary(package(sleepers(("a", 300, 0), ("b", 300, 0), ("c", 300, 0))), tmp_path)
    _proc, wall = run(exe, "--json", "-j", "1")
    assert wall >= 0.85, wall


def test_report_is_in_table_order_not_finish_order(package, tmp_path):
    """The first test finishes last; the report and outputs stay in table order."""
    specs = [("slow_fail", 900, 1), ("mid_fail", 500, 2), ("fast_fail", 100, 3), ("fast_pass", 50, 0)]
    exe = _binary(package(sleepers(*specs)), tmp_path)
    proc, _wall = run(exe, "--json", "-j", "4")
    report = json.loads(proc.stdout)
    assert [t["name"] for t in report["tests"]] == [n for n, _ms, _r in specs]
    by_name = {t["name"]: t for t in report["tests"]}
    for name, _ms, ret in specs:
        if ret:
            assert by_name[name]["exit_code"] == ret
            assert by_name[name]["output"] == f"{name} out\n", "each child has its own capture"
    assert proc.returncode == 1


def test_human_report_is_in_table_order(package, tmp_path):
    specs = [("first_slow", 600, 0), ("second_fast", 50, 0)]
    exe = _binary(package(sleepers(*specs)), tmp_path)
    proc, _wall = run(exe, "--no-color", "-j", "2")
    out = proc.stdout.decode()
    assert out.index("first_slow") < out.index("second_fast"), out


def test_timeouts_run_concurrently(package, tmp_path):
    """Each test's deadline is its own: 3 hangs under -j 3 time out together."""
    exe = _binary(package(HEADER + "".join(
        f"[[test]]\nfn hang_{i}() -> i32\n    loop\n        let x: i32 = 0\n    0\n\n"
        for i in range(3)) + "[[test]]\nfn ok() -> i32\n    0\n"), tmp_path)
    proc, wall = run(exe, "--json", "-j", "3", "-t", "500")
    report = json.loads(proc.stdout)
    assert report["summary"]["timeout"] == 3 and report["summary"]["passed"] == 1, report
    assert [t["status"] for t in report["tests"]] == ["timeout"] * 3 + ["pass"]
    assert wall < 1.3, wall


def test_a_long_test_does_not_delay_another_tests_timeout(package, tmp_path):
    """The wait ends at the earliest deadline, not when some child exits."""
    exe = _binary(package(sleepers(("sleeps", 1500, 0)) + (
        "[[test]]\nfn hangs() -> i32\n    loop\n        let x: i32 = 0\n    0\n")), tmp_path)
    proc, wall = run(exe, "--json", "-j", "2", "-t", "1000")
    report = json.loads(proc.stdout)
    statuses = {t["name"]: t["status"] for t in report["tests"]}
    assert statuses == {"sleeps": "timeout", "hangs": "timeout"}, report
    assert wall < 1.4, wall


def test_fail_fast_stops_at_first_failure_in_table_order(package, tmp_path):
    """Later tests finishing first are not reported: same report as -j 1 -x."""
    specs = [("ok_first", 50, 0), ("slow_fail", 500, 1), ("fast_pass", 10, 0), ("fast_fail", 10, 1)]
    exe = _binary(package(sleepers(*specs)), tmp_path)
    reports = []
    for jobs in ("1", "4"):
        proc, _wall = run(exe, "--json", "-x", "-j", jobs)
        assert proc.returncode == 1
        reports.append([(t["name"], t["status"]) for t in json.loads(proc.stdout)["tests"]])
    assert reports[0] == reports[1] == [("ok_first", "pass"), ("slow_fail", "fail")]


def test_json_has_no_short_flag_and_jobs_long_form_works(package, tmp_path):
    exe = _binary(package(sleepers(("a", 0, 0))), tmp_path)
    proc, _wall = run(exe, "--json", "--jobs", "2")
    assert json.loads(proc.stdout)["summary"]["passed"] == 1
    # `-j` takes a value now; it no longer means --json.
    proc, _wall = run(exe, "-j")
    assert proc.returncode == 1


@pytest.mark.parametrize("bad", ["0", "-3"])
def test_jobs_must_be_positive(package, tmp_path, bad):
    exe = _binary(package(sleepers(("a", 0, 0))), tmp_path)
    proc, _wall = run(exe, "--json", "-j", bad)
    assert proc.returncode == 1
    assert b"--jobs" in proc.stderr


def test_more_jobs_than_tests(package, tmp_path):
    exe = _binary(package(sleepers(("a", 0, 0), ("b", 0, 1))), tmp_path)
    proc, _wall = run(exe, "--json", "-j", "64")
    report = json.loads(proc.stdout)
    assert [(t["name"], t["status"]) for t in report["tests"]] == [("a", "pass"), ("b", "fail")]


def test_filter_and_jobs(package, tmp_path):
    exe = _binary(package(sleepers(("keep_a", 300, 0), ("drop", 300, 0), ("keep_b", 300, 0))), tmp_path)
    proc, wall = run(exe, "--json", "-j", "2", "-f", "keep*")
    report = json.loads(proc.stdout)
    assert [t["name"] for t in report["tests"]] == ["keep_a", "keep_b"]
    assert report["summary"]["skipped"] == 1
    assert wall < 0.55, wall


def test_children_do_not_inherit_the_blocked_sigchld(package, tmp_path):
    """The runner blocks SIGCHLD to wait for it; a test must not see that."""
    exe = _binary(package(HEADER + """\
[[test]]
fn sigchld_unblocked() -> i32
    var old: i64 = 0
    sys_rt_sigprocmask(SIG_BLOCK, null, @old, 8)
    ((old >> 16) & 1) as i32
"""), tmp_path)
    for jobs in ("1", "2"):
        proc, _wall = run(exe, "--json", "-j", jobs)
        assert json.loads(proc.stdout)["tests"][0]["status"] == "pass", proc.stdout
