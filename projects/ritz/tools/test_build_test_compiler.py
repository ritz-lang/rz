"""`build.py test --compiler X` must run tests with X.

AGAST #1500: `run_tests` took no compiler and hard-coded `RITZ0 --test`, so
every `build.py test --compiler ritz1` verdict was ritz0's. Until ritz1 had a
test mode, ritz1 runs were a named failure ("has no --test harness").

AGAST #1908: ritz1 emits the [[test]] table, so `ritz0 --test <file>
--compiler ritz1` builds the whole test binary with ritz1. Every ritz1-family
run must pass `--compiler`: a bare `--test` would be a silent fall back to
ritz0, the #1500 bug.

These tests point build.py's RITZ0 at a stub that records every invocation
and reports a passing harness summary.
"""

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]

STUB = textwrap.dedent(
    """\
    import os, sys
    with open(os.environ["RITZ0_STUB_LOG"], "a") as f:
        f.write(" ".join(sys.argv[1:]) + "\\n")
    print("1 passed, 0 failed")
    """
)


@pytest.fixture
def buildpy(request):
    # build.py does `from cache import BuildCache`, so its own directory must
    # be importable while we exec it by path. Loaded fresh per test so a
    # monkeypatched RITZ0 cannot leak between tests.
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_1500", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def stub_ritz0(tmp_path, monkeypatch, buildpy):
    """Record every `ritz0 --test` run build.py makes; return the log path.

    Since AGAST #1915 build.py runs the file in-process (test_runner.run_files,
    what `ritz0 --test` runs), and as a `ritz0.py --test` child only off the
    main thread. Both are stubbed to log the same `ritz0 --test` argv.
    """
    stub = tmp_path / "ritz0_stub.py"
    stub.write_text(STUB)
    log = tmp_path / "ritz0_calls.log"
    log.write_text("")
    monkeypatch.setenv("RITZ0_STUB_LOG", str(log))
    monkeypatch.setattr(buildpy, "RITZ0", stub)

    def run_files(files, verbose=False, compiler="ritz0"):
        with open(log, "a") as f:
            for path in files:
                f.write(f"--test {path}"
                        + ("" if compiler == "ritz0" else f" --compiler {compiler}") + "\n")
        print("1 passed, 0 failed")
        return 0
    monkeypatch.setattr(buildpy._test_runner(), "run_files", run_files)
    return log


@pytest.fixture
def test_only_pkg(tmp_path):
    """A tiny test-only package: no binary to build, two test files."""
    pkg = tmp_path / "fixture_pkg"
    (pkg / "test").mkdir(parents=True)
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "fixture_pkg"\nversion = "0.1.0"\n\n[build]\ntest_only = true\n'
    )
    body = "[[test]]\nfn test_ok() -> i32\n    0\n"
    (pkg / "test" / "test_a.ritz").write_text(body)
    (pkg / "test_b.ritz").write_text(body)  # root-level test_*.ritz (test-only glob)
    return pkg


def _run(buildpy, monkeypatch, pkg, compiler):
    monkeypatch.setattr(
        sys, "argv", ["build.py", "test", str(pkg), "--compiler", compiler, "--no-cache"]
    )
    return buildpy.main() or 0


@pytest.mark.unit
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_ritz1_family_builds_test_binaries_with_that_compiler(
    buildpy, stub_ritz0, test_only_pkg, monkeypatch, capsys, compiler
):
    rc = _run(buildpy, monkeypatch, test_only_pkg, compiler)
    calls = stub_ritz0.read_text().splitlines()
    text = capsys.readouterr().out

    assert rc == 0
    assert len(calls) == 2
    # Every harness run names the compiler; none is a bare (ritz0) `--test`.
    assert all(c.startswith("--test ") and c.endswith(f" --compiler {compiler}")
               for c in calls), calls
    assert {Path(c.split(" ")[1]).name for c in calls} == {"test_a.ritz", "test_b.ritz"}
    assert "has no --test harness" not in text
    assert "All tests passed" in text


@pytest.mark.unit
def test_ritz0_behaviour_unchanged(buildpy, stub_ritz0, test_only_pkg, monkeypatch, capsys):
    rc = _run(buildpy, monkeypatch, test_only_pkg, "ritz0")
    calls = stub_ritz0.read_text().splitlines()

    assert rc == 0
    assert len(calls) == 2
    assert all(c.startswith("--test ") for c in calls)
    assert {Path(c.split(" ", 1)[1]).name for c in calls} == {"test_a.ritz", "test_b.ritz"}
    assert "All tests passed" in capsys.readouterr().out


@pytest.mark.unit
def test_run_tests_defaults_to_ritz0(buildpy, stub_ritz0, test_only_pkg):
    # A caller that passes no compiler keeps today's behaviour.
    pkg_dir, config = buildpy.find_package_at(test_only_pkg)
    assert buildpy.run_tests(pkg_dir, config) is True
    assert len(stub_ritz0.read_text().splitlines()) == 2


@pytest.mark.unit
def test_normal_package_threads_compiler_to_run_tests(
    buildpy, stub_ritz0, test_only_pkg, monkeypatch, capsys
):
    # Same fixture minus test_only: cmd_test builds first (stubbed here to
    # succeed with the requested compiler) and then runs the test/ files.
    toml = test_only_pkg / "ritz.toml"
    toml.write_text(toml.read_text().replace("test_only = true", "test_only = false"))
    built_with = []

    class _Ok:
        ok = True

    def fake_build(pkg_dir, config, **kw):
        built_with.append(kw.get("compiler"))
        return _Ok()

    monkeypatch.setattr(buildpy, "build_package", fake_build)
    rc = _run(buildpy, monkeypatch, test_only_pkg, "ritz1")
    text = capsys.readouterr().out

    calls = stub_ritz0.read_text().splitlines()
    assert built_with == ["ritz1"]
    assert rc == 0
    # Only test/*.ritz: the root test_*.ritz glob is for test-only packages.
    assert len(calls) == 1 and calls[0].endswith("test_a.ritz --compiler ritz1"), calls
    assert "has no --test harness" not in text


@pytest.mark.unit
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_unit_file_entry_point_passes_the_compiler_on(
    buildpy, stub_ritz0, test_only_pkg, tmp_path, monkeypatch, compiler
):
    # `rz test --compiler X` fans files out through `--unit-file`; that entry
    # point must hand X to the harness, or rz's ritz1 runs are silently ritz0.
    result = tmp_path / "result.json"
    tfile = test_only_pkg / "test" / "test_a.ritz"
    monkeypatch.setattr(sys, "argv", [
        "build.py", "test", str(test_only_pkg), "--compiler", compiler,
        "--unit-file", str(tfile), "--unit-result", str(result),
    ])
    assert (buildpy.main() or 0) == 0
    calls = stub_ritz0.read_text().splitlines()
    want = f"--test {tfile}" + ("" if compiler == "ritz0" else f" --compiler {compiler}")
    assert calls == [want]
