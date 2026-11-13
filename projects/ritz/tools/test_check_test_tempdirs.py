"""Tests for tools/check_test_tempdirs.py (AGAST #2875)."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_test_tempdirs import find_violations, find_violations_in_source

RITZ_ROOT = Path(__file__).resolve().parent.parent
CHECK = Path(__file__).resolve().parent / "check_test_tempdirs.py"


def _lines(src: str) -> list[int]:
    return [lineno for lineno, _ in find_violations_in_source(textwrap.dedent(src))]


@pytest.mark.parametrize("src", [
    # the for_header / slice_string shape: a cached helper, no rmtree
    """
    import functools, tempfile
    @functools.cache
    def objects(c):
        work = tempfile.mkdtemp(prefix=f"x_{c}_")
        return work
    """,
    # the check_no_s_strings shape: a helper method, class has no cleanup
    """
    import tempfile
    class T:
        def _setup(self):
            return tempfile.mkdtemp(prefix="y_")
        def test_a(self):
            self._setup()
    """,
    # bare-name import; rmtree in a *different* function does not count
    """
    from tempfile import mkdtemp
    def make():
        return mkdtemp()
    def other(p):
        import shutil; shutil.rmtree(p)
    """,
])
def test_flags_leaks(src):
    assert len(_lines(src)) == 1


@pytest.mark.parametrize("src", [
    # cleanup in the same function
    """
    import shutil, tempfile
    def test_x():
        d = tempfile.mkdtemp()
        try:
            pass
        finally:
            shutil.rmtree(d)
    """,
    # setUp / tearDown
    """
    import shutil, tempfile, unittest
    class T(unittest.TestCase):
        def setUp(self):
            self.d = tempfile.mkdtemp()
        def tearDown(self):
            shutil.rmtree(self.d, ignore_errors=True)
    """,
    # global stored in pytest_configure, removed in pytest_unconfigure
    """
    import shutil, tempfile
    _D = None
    def pytest_configure(config):
        global _D
        _D = tempfile.mkdtemp()
    def pytest_unconfigure(config):
        shutil.rmtree(_D, ignore_errors=True)
    """,
    # atexit registration (of something other than rmtree)
    """
    import atexit, tempfile
    def a():
        d = tempfile.mkdtemp()
        atexit.register(remove_tree, d)
    """,
    # a cleanup_* helper
    """
    import tempfile
    def b():
        d = tempfile.mkdtemp()
        cleanup_scratch(d)
    """,
    # explicit pragma with a reason
    """
    import tempfile
    def make():
        return tempfile.mkdtemp()  # tempdir-ok: caller registers it
    """,
])
def test_accepts_cleaned_up(src):
    assert _lines(src) == []


def test_pragma_needs_a_reason():
    assert len(_lines("""
    import tempfile
    def make():
        return tempfile.mkdtemp()  # tempdir-ok:
    """)) == 1


def test_only_test_files_are_scanned(tmp_path):
    leak = "import tempfile\ndef f():\n    return tempfile.mkdtemp()\n"
    (tmp_path / "build.py").write_text(leak)
    (tmp_path / "test_a.py").write_text(leak)
    (tmp_path / "conftest.py").write_text(leak)
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "test_gen.py").write_text(leak)
    assert sorted(str(p) for p, _, _ in find_violations(tmp_path)) == ["conftest.py", "test_a.py"]


def test_cli_exit_codes(tmp_path):
    (tmp_path / "test_ok.py").write_text("x = 1\n")
    assert subprocess.run([sys.executable, str(CHECK), str(tmp_path)], check=False).returncode == 0
    (tmp_path / "test_bad.py").write_text("import tempfile\ntempfile.mkdtemp()\n")
    res = subprocess.run([sys.executable, str(CHECK), str(tmp_path)], capture_output=True, text=True, check=False)
    assert res.returncode == 1 and "test_bad.py:2" in res.stdout


def test_ritz_tree_has_no_leaking_mkdtemp():
    """The guard itself: every test file in projects/ritz cleans up its mkdtemp dirs."""
    violations = find_violations(RITZ_ROOT)
    assert not violations, "\n".join(f"{p}:{n}: {line}" for p, n, line in violations)
