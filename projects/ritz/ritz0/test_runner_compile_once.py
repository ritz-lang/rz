"""The ritz0 test harness must compile a test file once, not once per test.

AGAST #1633. `run_test_file` compiled dependencies once, then for every
`[[test]]` called `compile_test`, which re-ran ritz0 over the *whole* test file
(with a `main` appended that called that one test) and re-linked. Compiling
mausoleum's test_query.ritz costs ~25 s, so its 52 tests took ~22 minutes and
the file blew through build.py's 180 s per-file budget -- with every single
test passing.

The fix compiles one harness per file whose `main` dispatches on argc, links
it once, and runs the binary once per test. Each test still gets its own
process (and its own 10 s timeout), so a crash or hang stays attributed to the
test that caused it.

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
def test_each_test_still_runs_in_its_own_process(package, recorded_commands):
    """Compiling once must not collapse the tests into one process.

    A process per test is what keeps a crash, hang or `exit` attributed to the
    test that caused it, so the binary must still be executed once per test.
    """
    test_runner.run_test_file(str(package))

    runs = [
        c for c in recorded_commands
        if c and c[0] != "clang" and not c[0].endswith(("python", "python3"))
        and c[0] != sys.executable
    ]
    assert len(runs) == N_TESTS, f"expected {N_TESTS} test executions, got {runs}"


@pytest.mark.integration
def test_per_test_verdicts_are_preserved(package):
    """Dispatch must route each test to its own function, with today's exit codes.

    Pass/fail counts alone could hide a dispatcher that ran the wrong test for an
    index, so the failure messages are checked by name. `test_wide_fail` pins the
    i64 behaviour of the old `main() -> i32 { test() }` harness: the return value
    becomes the exit code.
    """
    passed, failed, failures = test_runner.run_test_file(str(package))

    assert (passed, failed) == (3, 2), failures
    failed_names = sorted(f.split(":", 1)[0] for f in failures)
    assert failed_names == ["test_assert_fails", "test_wide_fail"], failures
    by_name = {f.split(":", 1)[0]: f for f in failures}
    assert "assertion failed" in by_name["test_assert_fails"]
    assert "exited with code 3" in by_name["test_wide_fail"]


@pytest.mark.unit
def test_dispatch_main_maps_each_test_to_a_distinct_argc():
    """The generated `main` selects test i when argc == i + 2 (argv[0] + i + 1 args)."""
    tests = ["test_one", "test_two", "test_three"]
    src = test_runner.generate_dispatch_main(tests)

    assert "fn main(" in src
    lines = src.splitlines()
    for i, name in enumerate(tests):
        guard = next(n for n, line in enumerate(lines) if line.strip().endswith(f"== {i + 2}"))
        assert name in lines[guard + 1], f"argc {i + 2} does not call {name}:\n{src}"
    assert test_runner.dispatch_args(0) == ["t"]
    assert test_runner.dispatch_args(2) == ["t", "t", "t"]
