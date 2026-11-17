"""AGAST #3795: a test file that does not build is compile-failed, not failed.

`build.py test examples/tier1_basics/01_hello --compiler ritz1` printed

    ✗ test_hello.ritz — 0 passed, 7 failed

for a test file that did not parse: test_runner charged the compile error
to each of the file's seven [[test]] fns, so build.py's classify_test_file
saw "failed > 0" and called the file "fail". No test ran. That is the #1345
misreport (a compile error read as assertion failures) under a new name.

Now a file whose test binary cannot be built is counted as an error, not as
failed tests; `ritz0 --test`'s summary says so; and the compiler's first
diagnostic is the line build.py shows. Under every compiler: the build
error comes back the same way from ritz0 and the ritz1 family.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
for d in (str(RITZ_ROOT), str(RITZ_ROOT / "ritz0")):
    if d not in sys.path:
        sys.path.insert(0, d)

test_runner = importlib.import_module("test_runner")

# What ritz1 printed for 01_hello's test file (abridged paths).
RITZ1_ERROR = (
    "ritz1 failed for test_hello.ritz: /p/test_hello.ritz:144:62: "
    "error: unexpected 'c\"expected\"'\n"
    "note: /p/test_hello.ritz:91:1: cannot parse item starting at '[[ test'\n"
    "/p/test_hello.ritz: error: 1 top-level item(s) failed to parse; "
    "refusing to emit a partial module\n")
RITZ0_ERROR = ("ritz0 failed for harness: Compiler error: /tmp/x/t.ritz:5:12: "
               "Unknown function: nope\n")

TWO_TESTS = ("[[test]]\nfn test_a() -> i32\n    0\n\n"
             "[[test]]\nfn test_b() -> i32\n    0\n")


@pytest.fixture
def buildpy(tmp_path):
    spec = importlib.util.spec_from_file_location(
        f"ritz_buildpy_3795_{tmp_path.name}", RITZ_ROOT / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
@pytest.mark.parametrize("error, first", [
    (RITZ1_ERROR, "/p/test_hello.ritz:144:62: error: unexpected 'c\"expected\"'"),
    (RITZ0_ERROR, "Compiler error: /tmp/x/t.ritz:5:12: Unknown function: nope"),
    # A warning ahead of the error is not the diagnostic.
    ("ritz1 failed for t.ritz: t.ritz:1:1: warning: unused\nt.ritz:2:3: error: bad\n",
     "t.ritz:2:3: error: bad"),
    # No line says "error" (a link failure, say): the first line.
    ("ld: undefined symbol foo\nmore\n", "ld: undefined symbol foo"),
])
def test_first_diagnostic_is_the_compilers_first_error_line(error, first):
    assert test_runner.first_diagnostic(error) == first


@pytest.mark.unit
def test_a_build_error_is_one_errored_file_not_failed_tests(tmp_path, monkeypatch, capsys,
                                                             buildpy):
    t = tmp_path / "test_two.ritz"
    t.write_text(TWO_TESTS)
    monkeypatch.setattr(test_runner, "build_test_binary",
                        lambda *a, **k: (None, RITZ1_ERROR))

    rc = test_runner.run_files([str(t)], compiler="ritz1")
    out, err = capsys.readouterr()
    assert rc == 1
    assert "0 passed, 0 failed, 1 errored" in out
    assert "error: unexpected 'c\"expected\"'" in err  # the first diagnostic
    assert "refusing to emit a partial module" in out  # the whole of it
    # One entry for the file, not one per [[test]] fn.
    assert "- test_a:" not in out and "- test_b:" not in out
    assert buildpy.classify_test_file(rc, out)[0] == "error"


@pytest.mark.unit
def test_an_exception_in_the_runner_is_an_errored_file(tmp_path, monkeypatch, capsys,
                                                       buildpy):
    t = tmp_path / "test_two.ritz"
    t.write_text(TWO_TESTS)

    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(test_runner, "build_test_binary", boom)

    rc = test_runner.run_files([str(t)])
    out, err = capsys.readouterr()
    assert rc == 1
    assert "0 passed, 0 failed, 1 errored" in out
    assert "boom" in err
    assert buildpy.classify_test_file(rc, out)[0] == "error"


@pytest.mark.unit
def test_a_clean_run_prints_no_errored_count(tmp_path, monkeypatch, capsys):
    t = tmp_path / "test_two.ritz"
    t.write_text(TWO_TESTS)
    monkeypatch.setattr(test_runner, "run_test_file", lambda *a, **k: (2, 0, []))
    assert test_runner.run_files([str(t)]) == 0
    out = capsys.readouterr().out
    assert "2 passed, 0 failed" in out and "errored" not in out


@pytest.mark.unit
def test_classify_reads_an_errored_summary_as_error(buildpy):
    # A run of several files, one of which did not build: the
    # assertion failure elsewhere does not hide the compile failure.
    assert buildpy.classify_test_file(1, "3 passed, 0 failed, 1 errored\n")[0] == "error"
    assert buildpy.classify_test_file(1, "3 passed, 2 failed, 1 errored\n")[0] == "error"


# A file that parses but does not compile (an unknown function), under each
# compiler: the ritz1 family shares _ritz1_compile, so ritz1 stands for
# ritz1_selfhosted. And one that does not parse at all, which test_runner's
# own [[test]] discovery rejects before any compiler runs.
DOES_NOT_COMPILE = "[[test]]\nfn test_a() -> i32\n    assert nope() == 7\n    0\n"
DOES_NOT_PARSE = "[[test]]\nfn test_a() -> i32\n    assert )\n    0\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler, src, diag", [
    ("ritz0", DOES_NOT_COMPILE, "test_bad.ritz:3:"),
    ("ritz1", DOES_NOT_COMPILE, "test_bad.ritz:3:"),
    ("ritz0", DOES_NOT_PARSE, "test_bad.ritz"),
])
def test_a_test_file_that_does_not_build_is_compile_failed(compiler, src, diag, tmp_path,
                                                          capsys, buildpy, request):
    if compiler == "ritz1":
        request.getfixturevalue("ritz1_bin")
    pkg = tmp_path / "pkg"
    (pkg / "test").mkdir(parents=True)
    t = pkg / "test" / "test_bad.ritz"
    t.write_text(src + "\n" + TWO_TESTS.replace("test_a", "test_c"))

    got = buildpy.run_test_file(t, pkg, buildpy.test_env_for_files(),
                                buildpy.per_file_timeout(), compiler)
    out = capsys.readouterr().out
    assert got["status"] == "error", out
    shown = out.split("✗ test_bad.ritz — ", 1)[1].splitlines()[0]
    assert "passed," not in shown, out
    # The line shown is the compiler's diagnostic, naming the test file
    # (not test_runner's scratch copy of it) and the line it is on.
    assert shown.startswith("Error in test_bad.ritz: "), out
    assert diag in shown and "ritz_test_" not in shown, out
    # build.py cuts the line at 200 characters; the directory is left out.
    assert str(pkg) not in shown, out
