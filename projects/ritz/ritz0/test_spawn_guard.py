"""Tests for spawn_guard, the `integration` marker audit (AGAST #1805).

36 files that spawned ritz0/ritz1/clang carried no `integration` mark, so
`-m "not integration"` (the smoke tier's selection) silently included tests
that compile and link.  spawn_guard fails any test that starts a process —
in setup, call or teardown, directly or through ritz0_inproc — unless it is
marked `integration`.  It watches what the test actually does rather than
grepping its source, so it cannot be fooled by a helper imported from
another module, and it cannot flag a pure test for mentioning `subprocess`.

Each case runs a nested pytest over a scratch test file with the plugin
loaded by name, exactly as ritz0/conftest.py loads it.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ0_DIR = Path(__file__).resolve().parent


def _run(tmp_path, body):
    (tmp_path / "test_case.py").write_text(textwrap.dedent(body))
    env = dict(os.environ, PYTHONPATH=str(RITZ0_DIR))
    env.pop("PYTEST_XDIST_WORKER", None)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "spawn_guard",
         "-p", "no:cacheprovider", "-p", "no:xdist", str(tmp_path / "test_case.py")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )


def test_unmarked_spawn_fails(tmp_path):
    r = _run(tmp_path, """
        import subprocess
        def test_spawns():
            subprocess.run(["true"])
    """)
    assert r.returncode == 1, r.stdout
    assert "1 failed" in r.stdout
    assert "integration" in r.stdout and "true" in r.stdout


def test_marked_spawn_passes(tmp_path):
    r = _run(tmp_path, """
        import pytest, subprocess
        pytestmark = pytest.mark.integration
        def test_spawns():
            subprocess.run(["true"])
    """)
    assert r.returncode == 0, r.stdout


def test_pure_test_mentioning_subprocess_passes(tmp_path):
    r = _run(tmp_path, """
        import subprocess
        def test_pure():
            assert subprocess.PIPE == -1
    """)
    assert r.returncode == 0, r.stdout


def test_spawn_in_fixture_setup_fails(tmp_path):
    r = _run(tmp_path, """
        import pytest, subprocess
        @pytest.fixture(scope="module")
        def built():
            subprocess.run(["true"])
        def test_uses(built):
            pass
    """)
    assert r.returncode == 1, r.stdout
    assert "1 error" in r.stdout or "1 failed" in r.stdout


def test_inproc_ritz0_counts_as_a_spawn(tmp_path):
    r = _run(tmp_path, """
        from ritz0_inproc import ritz0_oracle
        def test_oracle():
            ritz0_oracle("pub fn main() -> i32\\n    0\\n")
    """)
    assert r.returncode == 1, r.stdout
    assert "ritz0" in r.stdout


def test_os_system_counts_as_a_spawn(tmp_path):
    r = _run(tmp_path, """
        import os
        def test_shell():
            os.system("true")
    """)
    assert r.returncode == 1, r.stdout
