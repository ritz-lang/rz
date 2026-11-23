"""shellcheck is a pinned dependency, so its tests fail without it (AGAST #4360).

The gate hosts had no shellcheck, so every shellcheck test skipped there and a
shell finding failed CI only (#4359, #4264).  shellcheck-py, a wheel carrying
the static shellcheck binary, is now pinned in requirements-dev.txt and
requirements.lock, so CI and every gate venv install the same shellcheck from
the same install line.  ritz0/harness/shellcheck_tool.py hands it to the
tests: a missing or wrong-version shellcheck is a failure, never a skip.
"""

import ast
import re
import shutil
from pathlib import Path

import pytest

import shellcheck_tool

RITZ_ROOT = Path(__file__).resolve().parents[1]
LOCK = RITZ_ROOT / "requirements.lock"
DEV_REQS = RITZ_ROOT / "requirements-dev.txt"


def _lock_pin(name):
    m = re.search(rf"^{re.escape(name)}==(\S+)", LOCK.read_text(), re.M)
    return m and m.group(1)


@pytest.mark.unit
def test_requirements_dev_declares_shellcheck_py():
    reqs = [line.split("#", 1)[0].strip() for line in DEV_REQS.read_text().splitlines()]
    assert any(re.match(r"shellcheck-py\b", r) for r in reqs), (
        "shellcheck-py is not in requirements-dev.txt: the gate venv would have no shellcheck"
    )


@pytest.mark.unit
def test_lock_pins_shellcheck_py_to_cis_0_11():
    # The runner's own shellcheck was 0.11 when #4359 found the drift; the
    # pin keeps CI and the gates on one version from now on.
    assert _lock_pin("shellcheck-py") == "0.11.0.1"


@pytest.mark.unit
def test_expected_version_comes_from_the_lock():
    # shellcheck-py's 4th component is the wrapper's own release.
    assert shellcheck_tool.expected_version() == "0.11.0"


@pytest.mark.unit
@pytest.mark.parametrize(
    "out, version",
    [
        ("ShellCheck - shell script analysis tool\nversion: 0.11.0\nlicense: GNU GPLv3\n", "0.11.0"),
        ("version: 0.9.0\n", "0.9.0"),
        ("no version here\n", None),
    ],
)
def test_parse_version(out, version):
    assert shellcheck_tool.parse_version(out) == version


@pytest.mark.unit
def test_missing_shellcheck_fails_and_names_the_install_line(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    # BaseException, not Failed: a pytest.skip inside raises(Failed) would
    # propagate and skip this test, which is the very bug it guards.
    with pytest.raises(BaseException) as e:
        shellcheck_tool.shellcheck()
    assert e.type is pytest.fail.Exception, e.type
    assert "requirements.lock" in str(e.value)


@pytest.mark.unit
def test_a_different_version_fails():
    with pytest.raises(pytest.fail.Exception) as e:
        shellcheck_tool.check_version("/usr/bin/shellcheck", "version: 0.9.0\n")
    assert "0.9.0" in str(e.value) and "0.11.0" in str(e.value)


@pytest.mark.unit
def test_the_pinned_version_passes():
    shellcheck_tool.check_version("/x/shellcheck", "version: 0.11.0\n")


def _which_shellcheck_calls(path):
    tree = ast.parse(path.read_text(), str(path))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "which"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "shellcheck"
        ):
            yield node.lineno


@pytest.mark.unit
def test_no_test_looks_shellcheck_up_itself():
    """A test that finds shellcheck with shutil.which can skip without it,
    which is how the gate never ran these (#4360).  They all go through
    shellcheck_tool.shellcheck(), which fails instead."""
    offenders = [
        f"{p.relative_to(RITZ_ROOT)}:{line}"
        for d in ("ritz0", "tools")
        for p in sorted((RITZ_ROOT / d).rglob("test_*.py"))
        for line in _which_shellcheck_calls(p)
    ]
    assert not offenders, offenders


# Spawns `shellcheck --version`.
@pytest.mark.integration
def test_this_venv_has_the_pinned_shellcheck():
    """Fails on a gate host whose venv predates the pin: re-run the install
    line from the failure message in the host's shared venv."""
    assert Path(shellcheck_tool.shellcheck()).is_file()
