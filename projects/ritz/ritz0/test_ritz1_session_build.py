"""AGAST #1804: ritz1 is built once per pytest session, by conftest.py.

The suite runs under pytest-xdist.  If test modules still ran their own
`make -C ritz1 ritz1`, several workers would run make on one `ritz1/build/`
at once, racing on its .d.tmp/.ll/.o files, and a serial run would pay for ~80
no-op makes.  So exactly one place may build ritz1: the `ritz1_bin` session
fixture in conftest.py.  These tests pin that:

  * static: no test module builds ritz1 or the runtime start object itself, or
    defines its own `ritz1_bin` fixture that would shadow the session one;
  * dynamic: a real xdist session (2 workers, two ritz1 modules) and a real
    serial session each run make on ritz1 exactly once, counted through
    conftest's RITZ_TEST_MAKE_LOG hook.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# xdist_group("tree") (AGAST #1804): the nested sessions run make on the real
# ritz1/ and runtime/ (a no-op when current, but still make in the shared
# tree).  Tests in the group run on one xdist worker, one at a time; see
# conftest.py.
pytestmark = pytest.mark.xdist_group("tree")


HERE = Path(__file__).resolve().parent

# Two modules that need ritz1, so a per-module build would show up as two makes.
NESTED_TESTS = ["test_ritz1_pub_var.py", "test_ritz1_bool_fields.py"]

# A make invocation aimed at ritz1/ or runtime/, in any of the shapes the
# deleted helpers used: ["make", "-C", "ritz1", ...] or _make("ritz1", ...).
_MAKE_IN_TREE = re.compile(
    r"""["']-C["']\s*,\s*["'](ritz1|runtime)["']"""
    r"""|_make\(\s*["'](ritz1|runtime)["']"""
)


def _test_modules() -> list[Path]:
    return [p for p in sorted(HERE.glob("test_*.py")) if p.name != Path(__file__).name]


def _fixture_names(source: str) -> list[str]:
    """Names of functions decorated with @pytest.fixture (any form)."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "fixture":
                names.append(node.name)
    return names


@pytest.mark.unit
def test_make_pattern_is_live():
    """The scanner must recognise the shapes it is meant to forbid."""
    assert _MAKE_IN_TREE.search('["make", "-C", "ritz1", "ritz1"]')
    assert _MAKE_IN_TREE.search('["make", "-C", "runtime", RITZ_START.name]')
    assert _MAKE_IN_TREE.search('_make("runtime", RITZ_START.name, RITZ_START)')
    assert not _MAKE_IN_TREE.search('["make", "-C", str(tmp_path)]')
    assert _fixture_names(
        "import pytest\n"
        "@pytest.fixture(scope='module')\ndef ritz1_bin(): pass\n"
        "@pytest.fixture\ndef other(): pass\n"
    ) == ["ritz1_bin", "other"]


@pytest.mark.unit
def test_no_test_module_builds_ritz1_itself():
    offenders = []
    for path in _test_modules():
        text = path.read_text()
        for lineno, line in enumerate(text.splitlines(), 1):
            if _MAKE_IN_TREE.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
        if "ritz1_bin" in _fixture_names(text):
            offenders.append(f"{path.name}: defines its own ritz1_bin fixture")
    assert not offenders, (
        "only conftest.py may build ritz1 / the runtime start object; under "
        "xdist a per-module make races other workers on ritz1/build/.  Request "
        "the `ritz1_bin` session fixture instead:\n  " + "\n  ".join(offenders)
    )


def _nested_pytest(tmp_path: Path, *extra: str, env: dict | None = None) -> tuple[subprocess.CompletedProcess, list[str]]:
    log = tmp_path / "make.log"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *extra, *NESTED_TESTS],
        cwd=HERE,
        env=dict(env or os.environ, RITZ_TEST_MAKE_LOG=str(log)),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    lines = log.read_text().splitlines() if log.exists() else []
    return proc, lines


def _ritz1_makes(lines: list[str]) -> list[str]:
    return [line for line in lines if re.search(r"-C ritz1 ritz1$", line)]


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["serial", "xdist"])
def test_session_builds_ritz1_exactly_once(tmp_path, mode):
    # -q is in the base args; two -v nets verbosity 1, which prints [gwN] per test.
    extra = ("-n", "2", "--dist", "loadgroup", "-v", "-v") if mode == "xdist" else ()
    proc, lines = _nested_pytest(tmp_path, *extra)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, f"nested {mode} run failed:\n{out[-6000:]}"
    # Non-vacuity: both modules ran, and the xdist arm really used workers.
    assert re.search(r"(\d+) passed", out) and int(re.search(r"(\d+) passed", out).group(1)) >= 4, out[-3000:]
    if mode == "xdist":
        assert "[gw0]" in out and "[gw1]" in out, f"tests did not run on 2 workers:\n{out[-3000:]}"
    makes = _ritz1_makes(lines)
    assert len(makes) == 1, (
        f"expected exactly one `make -C ritz1 ritz1` in a {mode} session, "
        f"got {len(makes)}:\n" + "\n".join(lines)
    )
    assert any("-C runtime" in line for line in lines), lines


# Loaded with -p into a nested session: as soon as conftest.py registers, its
# build is replaced by one that reports failure — before the serial fixture or
# the xdist controller's pytest_configure_node can call it.
_FAIL_PLUGIN = """
def pytest_plugin_registered(plugin, plugin_name, manager):
    if hasattr(plugin, "build_ritz1_artifacts") and hasattr(plugin, "ritz1_bin"):
        plugin.build_ritz1_artifacts = lambda: "INJECTED ritz1 build failure"
"""


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["serial", "xdist"])
def test_failed_session_build_fails_tests_never_skips(tmp_path, mode):
    """A broken ritz1 build must turn every ritz1 test red, not skip it (#1327)."""
    (tmp_path / "inject_ritz1_failure.py").write_text(_FAIL_PLUGIN)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(
        p for p in (str(tmp_path), os.environ.get("PYTHONPATH", "")) if p))
    extra = ("-p", "inject_ritz1_failure", "-rfs")
    if mode == "xdist":
        extra += ("-n", "2", "--dist", "loadgroup")
    proc, _ = _nested_pytest(tmp_path, *extra, env=env)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1, f"expected test failures (exit 1):\n{out[-4000:]}"
    assert "INJECTED ritz1 build failure" in out, out[-4000:]
    # A fixture failure is reported as an `error` at setup; either counts.
    red = sum(int(n) for n in re.findall(r"(\d+) (?:failed|errors?)\b", out))
    assert red >= 4, out[-4000:]
    # The ritz0 arms of these modules do not request ritz1 and still pass.
    assert not re.search(r"\d+ skipped\b", out), (
        f"a failed ritz1 build must fail every test that needs it:\n{out[-4000:]}")


# Tests that must lead the collection order (AGAST #1804): the longest single
# test, and the members of the serial `tree` group.
_FRONT = re.compile(
    r"^(test_ritz1_bin_staleness\.py::"
    r"|test_build_compiler_switch\.py::|test_ritzlib_output_goldens\.py::"
    r"|test_import_alias_match_arm\.py::|test_ritz1_session_build\.py::"
    r"|test_build\.py::Test\w+::test_(build_exits_nonzero|package_builds_when))"
)


@pytest.mark.integration
def test_long_and_grouped_tests_are_scheduled_first():
    """xdist hands out work in collection order, so the longest single test
    (the staleness meta-test) and the serial `tree` group must lead it, or
    they become the tail of a parallel run."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=HERE, capture_output=True, text=True, timeout=600,
    )
    ids = [line for line in proc.stdout.splitlines() if "::" in line]
    assert proc.returncode == 0 and len(ids) > 1000, proc.stdout[-2000:] + proc.stderr[-2000:]
    flags = [bool(_FRONT.match(i)) for i in ids]
    assert flags[0] and ids[0].startswith("test_ritz1_bin_staleness.py::"), ids[:5]
    first_other = flags.index(False)
    late = [i for i, f in zip(ids[first_other:], flags[first_other:]) if f]
    assert not late, f"slow/grouped tests collected after ordinary ones: {late[:5]}"
