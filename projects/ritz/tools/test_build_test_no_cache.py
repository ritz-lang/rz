"""`build.py test --no-cache` bypasses the artifact store for test binaries.

AGAST #4626: `--no-cache` reached only the package build (compile_binary's
`use_cache`); every test file's binary was still built by test_runner, which
fetches its dependencies' objects and its harness from the shared store
unless RITZ_NO_CAS is set. A stale store object kept failing a test link
"with --no-cache". Now the flag puts RITZ_NO_CAS=1 in the test files'
environment, in both the serial run and `--unit-file` (`rz test -j`).

test_runner.run_files is stubbed to record the RITZ_NO_CAS it runs under.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def buildpy(request, monkeypatch):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_4626", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    return mod


@pytest.fixture
def seen(buildpy, monkeypatch):
    """RITZ_NO_CAS as each in-process test file run saw it."""
    record = []

    def run_files(files, verbose=False, compiler="ritz0"):
        record.extend(os.environ.get("RITZ_NO_CAS") for _ in files)
        print("1 passed, 0 failed")
        return 0
    monkeypatch.setattr(buildpy._test_runner(), "run_files", run_files)
    return record


@pytest.fixture
def pkg(tmp_path):
    pkg = tmp_path / "fixture_pkg"
    (pkg / "test").mkdir(parents=True)
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "fixture_pkg"\nversion = "0.1.0"\n\n[build]\ntest_only = true\n')
    (pkg / "test" / "test_a.ritz").write_text("[[test]]\nfn test_ok() -> i32\n    0\n")
    return pkg


def _main(buildpy, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["build.py", "test", *map(str, argv)])
    return buildpy.main() or 0


@pytest.mark.unit
@pytest.mark.parametrize("flags, expected", [((), None), (("--no-cache",), "1")])
def test_serial_run(buildpy, seen, pkg, monkeypatch, flags, expected):
    assert _main(buildpy, monkeypatch, pkg, *flags) == 0
    assert seen == [expected]
    assert "RITZ_NO_CAS" not in os.environ  # the test env only, not this process


@pytest.mark.unit
@pytest.mark.parametrize("flags, expected", [((), None), (("--no-cache",), "1")])
def test_unit_file(buildpy, seen, pkg, tmp_path, monkeypatch, flags, expected):
    result = tmp_path / "result.json"
    assert _main(buildpy, monkeypatch, pkg, "--unit-file", pkg / "test" / "test_a.ritz",
                 "--unit-result", result, *flags) == 0
    assert seen == [expected]
