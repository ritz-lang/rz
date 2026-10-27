"""The ritz0 test harness must compile a test file once, not once per test.

AGAST #1633. `run_test_file` compiled dependencies once, then for every
`[[test]]` called `compile_test`, which re-ran ritz0 over the *whole* test file
(with a `main` appended that called that one test) and re-linked. Compiling
mausoleum's test_query.ritz costs ~25 s, so its 52 tests took ~22 minutes and
the file blew through build.py's 180 s per-file budget -- with every single
test passing.

The fix compiles one harness per file and links it once. Since AGAST #1868 that
harness is the test binary of LANGUAGE_SPEC §17.1 -- the file in test mode
plus ritzunit as `main` -- run once; ritzunit forks a child per test, so each
test still gets its own process (and its own 10 s timeout) and a crash or
hang stays attributed to the test that caused it.

These tests count the compiler and linker invocations rather than timing them:
a wall-clock assertion would be flaky on a loaded CI box, while "one ritz0 run
for the harness, one clang run" is exact and is the property that matters.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parent.resolve()
RITZ_DIR = RITZ0_DIR.parent
sys.path.insert(0, str(RITZ0_DIR))

import test_runner  # noqa: E402

# Covers every return shape found in the tree (`-> i32`, `-> i64`, none),
# a passing and a failing test of each interesting kind, a helper the tests
# share, and a pre-existing `main` that the harness must replace.
TEST_SOURCE = textwrap.dedent(
    """\
    import ritzlib.sys

    fn helper() -> i32
        7

    [[test]]
    fn test_pass() -> i32
        assert helper() == 7
        0

    [[test]]
    fn test_assert_fails() -> i32
        assert helper() == 8
        0

    [[test]]
    fn test_unit()
        assert helper() == 7

    [[test]]
    fn test_wide_pass() -> i64
        0

    [[test]]
    fn test_wide_fail() -> i64
        3

    fn main() -> i32
        42
    """
)

N_TESTS = 5


@pytest.fixture
def package(tmp_path, monkeypatch):
    """A minimal package whose only dependency is ritzlib."""
    monkeypatch.setenv("RITZ_PATH", str(RITZ_DIR))
    # AGAST #1915: the harness now comes from the artifact store when it has
    # it. A shared store warmed by an earlier run (or another xdist worker)
    # would serve it with 0 compiles, so count against a private, empty one.
    monkeypatch.setenv("RITZ_CACHE_DIR", str(tmp_path / "cas"))
    (tmp_path / "ritz.toml").write_text(
        textwrap.dedent(
            f"""\
            [package]
            name = "compile_once"
            version = "0.1.0"
            sources = ["test"]

            [dependencies]
            ritzlib = {{ path = "{RITZ_DIR / 'ritzlib'}", sources = ["."] }}
            """
        )
    )
    (tmp_path / "test").mkdir()
    test_file = tmp_path / "test" / "test_compile_once.ritz"
    test_file.write_text(TEST_SOURCE)
    return test_file


@pytest.fixture
def recorded_commands(monkeypatch):
    """Record every subprocess command test_runner runs, then run it for real."""
    calls = []
    real_run = subprocess.run

    def recording_run(cmd, *args, **kwargs):
        calls.append(list(map(str, cmd)))
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(test_runner.subprocess, "run", recording_run)
    return calls


def _harness_compiles(calls):
    """ritz0 runs that produce an executable entry point (i.e. not libraries)."""
    return [
        c for c in calls
        if len(c) > 1 and c[1].endswith("ritz0.py") and "--no-runtime" not in c
    ]


def _links(calls):
    return [c for c in calls if c and c[0] == "clang"]


@pytest.mark.integration
def test_test_file_is_compiled_once_regardless_of_test_count(package, recorded_commands):
    """The defect itself: N tests used to mean N full compiles and N links."""
    test_runner.run_test_file(str(package))

    harness = _harness_compiles(recorded_commands)
    links = _links(recorded_commands)
    assert len(harness) == 1, (
        f"test file compiled {len(harness)} times for {N_TESTS} tests; "
        "it must be compiled once per file"
    )
    assert len(links) == 1, (
        f"harness linked {len(links)} times for {N_TESTS} tests; "
        "it must be linked once per file"
    )


@pytest.mark.integration
def test_binary_runs_once_and_ritzunit_forks_per_test(package, recorded_commands):
    """One execution of the binary; isolation is ritzunit's fork per test.

    The report has one entry per test, so every test ran, in its own child.
    """
    passed, failed, _ = test_runner.run_test_file(str(package))

    runs = [
        c for c in recorded_commands
        if c and c[0] not in ("clang", "ld", "objcopy")
        and not c[0].endswith(("python", "python3")) and c[0] != sys.executable
    ]
    assert len(runs) == 1, f"expected one run of the test binary, got {runs}"
    assert passed + failed == N_TESTS


@pytest.mark.integration
def test_per_test_verdicts_are_preserved(package):
    """Each test's verdict is reported against its own name.

    Pass/fail counts alone could hide a runner that ran the wrong function for
    an entry, so the failure messages are checked by name. `test_wide_fail`
    returns 3 from `-> i64`: a non-i32 result fails as 1 (§17.1), it is not
    truncated into an exit status.
    """
    passed, failed, failures = test_runner.run_test_file(str(package))

    assert (passed, failed) == (3, 2), failures
    failed_names = sorted(f.split(":", 1)[0] for f in failures)
    assert failed_names == ["test_assert_fails", "test_wide_fail"], failures
    by_name = {f.split(":", 1)[0]: f for f in failures}
    assert "assertion failed" in by_name["test_assert_fails"]
    assert "exited with code 1" in by_name["test_wide_fail"]
