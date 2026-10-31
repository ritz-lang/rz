"""AGAST #1868: a test binary is the test file + ritzunit, and ritzunit is right.

`ritz0 --test` builds one binary per test file: the file compiled in test mode
(its `[[test]]` table, LANGUAGE_SPEC §17.1) linked with ritzunit's runner as
`main`, run once with `--json`. These tests drive that path end to end and pin
the ritzunit defects the ticket names:

  (c) discovery is the `[[test]]` attribute, not the `test_` name prefix;
  (d) the exit status is 0/1, not the failure count mod 256;
  (e) a test that prints cannot corrupt the --json report;
  and a test returning 256 fails, crashes and timeouts are attributed to
  their test, the runner's own symbols cannot clash with the program's.
"""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parent.resolve()
RITZ_DIR = RITZ0_DIR.parent
sys.path.insert(0, str(RITZ0_DIR))

import test_runner  # noqa: E402

# Every test builds and runs a binary.
pytestmark = pytest.mark.integration

# AGAST #1909: every test below runs both sequentially and under `-j 4`, so
# crash, timeout and output attribution are pinned for the pool too. This is
# the `-j` value `_run` and test_runner add to every run (None: no `-j`).
_jobs = None


@pytest.fixture(params=[None, 4], ids=["seq", "j4"], autouse=True)
def jobs(request, monkeypatch):
    global _jobs
    _jobs = request.param
    if request.param is not None:
        base = test_runner.runner_args
        monkeypatch.setattr(test_runner, "runner_args",
                            lambda: base() + ["-j", str(request.param)])
    yield request.param
    _jobs = None


@pytest.fixture
def package(tmp_path, monkeypatch):
    """Write a package with `test/<name>.ritz` (and optional `src/` modules)."""
    monkeypatch.setenv("RITZ_PATH", str(RITZ_DIR))
    (tmp_path / "ritz.toml").write_text(textwrap.dedent(f"""\
        [package]
        name = "harness_case"
        version = "0.1.0"
        sources = ["src"]

        [dependencies]
        ritzlib = {{ path = "{RITZ_DIR / 'ritzlib'}", sources = ["."] }}
        """))
    (tmp_path / "test").mkdir()
    (tmp_path / "src").mkdir()

    def write(source: str, modules: dict = None) -> Path:
        for name, text in (modules or {}).items():
            (tmp_path / "src" / f"{name}.ritz").write_text(textwrap.dedent(text))
        test_file = tmp_path / "test" / "test_case.ritz"
        test_file.write_text(textwrap.dedent(source))
        return test_file

    return write


def _binary(test_file: Path, tmp_path: Path) -> str:
    scratch = tmp_path / "scratch"
    scratch.mkdir(exist_ok=True)
    exe, error = test_runner.build_test_binary(str(test_file), str(scratch))
    assert error is None, error
    return exe


def _run(exe: str, *args: str) -> subprocess.CompletedProcess:
    extra = ["-j", str(_jobs)] if _jobs is not None else []
    return subprocess.run([exe, *args, *extra], capture_output=True, timeout=120)


def test_attribute_not_name_prefix_decides_what_runs(package, tmp_path):
    """(c) `fn test_helper` is not a test; `[[test]] fn check_x` is."""
    exe = _binary(package("""\
        fn test_helper_returns_failure() -> i32
            1

        [[test]]
        fn check_x() -> i32
            test_helper_returns_failure() - 1
        """), tmp_path)
    proc = _run(exe, "--json")
    report = json.loads(proc.stdout)
    assert [t["name"] for t in report["tests"]] == ["check_x"]
    assert report["tests"][0]["status"] == "pass"
    assert proc.returncode == 0


def test_three_hundred_failures_exit_nonzero(package, tmp_path):
    """(d) ritzunit exited with the failure count: 256 failures exited 0."""
    tests = "".join(f"[[test]]\nfn fails_{i}() -> i32\n    1\n\n" for i in range(300))
    test_file = package(tests)
    proc = _run(_binary(test_file, tmp_path), "--json")
    report = json.loads(proc.stdout)
    assert report["summary"]["failed"] == 300
    assert len(report["tests"]) == 300, "no silent cap on recorded results"
    assert proc.returncode == 1

    assert test_runner.run_test_file(str(test_file))[:2] == (0, 300)


def test_printing_tests_leave_json_parseable(package, tmp_path):
    """(e) Child output used to go straight to the runner's stdout."""
    exe = _binary(package("""\
        import ritzlib.io
        import ritzlib.sys

        [[test]]
        fn prints_and_passes() -> i32
            prints("{ not json\\n")
            0

        [[test]]
        fn prints_and_fails() -> i32
            prints("quote \\" backslash \\\\ tab \\t bell ")
            var bell: [1]u8
            bell[0] = 7
            sys_write(1, @bell[0], 1)
            prints(" done\\n")
            eprints("on stderr\\n")
            3
        """), tmp_path)
    proc = _run(exe, "--json")
    report = json.loads(proc.stdout)  # the assertion: it parses
    by_name = {t["name"]: t for t in report["tests"]}
    assert "output" not in by_name["prints_and_passes"]
    failed = by_name["prints_and_fails"]
    assert failed["exit_code"] == 3
    assert failed["output"] == 'quote " backslash \\ tab \t bell \x07 done\non stderr\n'


def test_human_output_shows_a_failing_tests_output(package, tmp_path):
    exe = _binary(package("""\
        import ritzlib.io

        [[test]]
        fn says_why() -> i32
            eprints("the reason\\n")
            1
        """), tmp_path)
    proc = _run(exe, "--no-color")
    assert proc.returncode == 1
    assert b"the reason" in proc.stdout


def test_result_256_fails(package, tmp_path):
    """An exit status keeps 8 bits: a test returning 256 used to pass."""
    test_file = package("""\
        [[test]]
        fn returns_256() -> i32
            256

        [[test]]
        fn returns_256_wide() -> i64
            256
        """)
    passed, failed, failures = test_runner.run_test_file(str(test_file))
    assert (passed, failed) == (0, 2), failures


def test_crash_assert_and_timeout_are_attributed(package, tmp_path, monkeypatch):
    monkeypatch.setattr(test_runner, "TEST_TIMEOUT_MS", 300)
    test_file = package("""\
        [[test]]
        fn crashes() -> i32
            # A load from address 0 the optimiser cannot see. `*(0 as *i32)`
            # is UB: the -O2 harness folded it to `unreachable` (AGAST #1917).
            asm x86_64:
                movl 0, %eax
            0

        [[test]]
        fn asserts() -> i32
            assert 1 == 2
            0

        [[test]]
        fn hangs() -> i32
            loop
                let x: i32 = 0
            0

        [[test]]
        fn passes() -> i32
            0
        """)
    passed, failed, failures = test_runner.run_test_file(str(test_file))
    assert (passed, failed) == (1, 3), failures
    by_name = {f.split(":", 1)[0]: f for f in failures}
    assert "crashed with signal 11" in by_name["crashes"]
    assert "assertion failed" in by_name["asserts"]
    assert "timeout" in by_name["hangs"]


def test_runner_symbols_cannot_clash_with_the_program(package, tmp_path):
    """The runner is linked with every symbol but `main` made local.

    Dependency modules are compiled with external linkage, and ritzunit
    defines names packages define too (spire has `run_tests`/`parse_args`,
    http a whole `json_record_*` stub). Unlocalized, this does not link.

    The same holds for the ritzlib modules only the runner imports: mausoleum
    defines `string_contains`, which ritzlib.string (pulled in by ritzunit,
    not by mausoleum's tests) defines too.
    """
    test_file = package("""\
        import harness_case.clash

        [[test]]
        fn uses_clashing_names() -> i32
            run_tests() + parse_args() + json_record_pass() + string_contains()
        """, modules={"clash": """\
        var g_verbose: i32 = 0

        pub fn run_tests() -> i32
            0

        pub fn parse_args() -> i32
            0

        pub fn json_record_pass() -> i32
            g_verbose = 0
            g_verbose

        pub fn string_contains() -> i32
            0
        """})
    assert test_runner.run_test_file(str(test_file))[:2] == (1, 0)


def test_runner_arguments_reach_the_runner(package, tmp_path):
    """`main(argc, argv)` gets real arguments: --list and --filter work."""
    exe = _binary(package("""\
        [[test]]
        fn alpha() -> i32
            0

        [[test]]
        fn beta() -> i32
            1
        """), tmp_path)
    listed = _run(exe, "--list")
    assert b"alpha" in listed.stdout and b"beta" in listed.stdout
    filtered = _run(exe, "--json", "-f", "alpha")
    report = json.loads(filtered.stdout)
    assert [t["name"] for t in report["tests"]] == ["alpha"]
    assert filtered.returncode == 0
