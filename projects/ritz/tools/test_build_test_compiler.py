"""`build.py test --compiler X` must run tests with X, or say plainly it did not.

AGAST #1500: `run_tests` took no compiler and hard-coded `RITZ0 --test`, so
every `build.py test --compiler ritz1` verdict was ritz0's. For test-only
packages the entire "ritz1" result was produced without ritz1 ever running.

ritz1 has no `--test` harness yet, so the honest answer for ritz1 and
ritz1_selfhosted is a named, FAILING verdict -- never a silent fall back to
ritz0 and never a skip that reads green.

These tests point build.py's RITZ0 at a stub that records every invocation
and reports a passing harness summary. If ritz1 fell back to ritz0 the stub
would make the run look green; the assertions catch both halves of that.
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
    """Point build.py's RITZ0 at a call-recording stub; return the log path."""
    stub = tmp_path / "ritz0_stub.py"
    stub.write_text(STUB)
    log = tmp_path / "ritz0_calls.log"
    log.write_text("")
    monkeypatch.setenv("RITZ0_STUB_LOG", str(log))
    monkeypatch.setattr(buildpy, "RITZ0", stub)
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
def test_ritz1_family_never_runs_ritz0_and_fails(
    buildpy, stub_ritz0, test_only_pkg, monkeypatch, capsys, compiler
):
    rc = _run(buildpy, monkeypatch, test_only_pkg, compiler)
    out = capsys.readouterr()
    text = out.out + out.err

    assert stub_ritz0.read_text() == "", f"ritz0 was invoked for --compiler {compiler}"
    assert rc != 0, "a test run that ran nothing must not exit 0"
    assert f"✗ fixture_pkg: {compiler} has no --test harness; 2 test file(s) NOT run" in text
    assert "All tests passed" not in text


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

    assert built_with == ["ritz1"]
    assert stub_ritz0.read_text() == ""
    assert rc != 0
    # Only test/*.ritz: the root test_*.ritz glob is for test-only packages.
    assert "✗ fixture_pkg: ritz1 has no --test harness; 1 test file(s) NOT run" in text
