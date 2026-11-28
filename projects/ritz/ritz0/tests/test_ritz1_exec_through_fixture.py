"""AGAST #5005: every test that runs a ritz1 binary goes through its fixture.

`test_ref_into_value._emit` ran `ritz1/build/<compiler>` after checking only
that the file existed, from rows that asked for no fixture, and
test_array_into_pointer imports it.  Under xdist one such row exec'd ritz1
while `make -C ritz1 ritz1` (a nested session's, in test_ritz1_session_build)
relinked it in place: `PermissionError: [Errno 13]`, or the file missing.

Two halves fix it.  ritz1/Makefile links atomically and no longer goes stale
when build.py rewrites the shared runtime shim (tools/test_ritz1_incremental_
deps.py pins both).  And here: a row parametrized with a ritz1 compiler's name
gets that compiler's fixture (conftest item 15), and a test module that names
a ritz1 binary path either asks for a fixture itself or carries such rows.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import conftest

RITZ0 = Path(__file__).resolve().parents[1]

# Names a module binds to a ritz1 build product (conftest.py's spelling, and
# the per-module copies of it).
_PATH_NAMES = {"RITZ1_BUILD", "RITZ1_BIN", "RITZ1_SELFHOSTED"}
_FIXTURES = set(conftest._BUILD_FIXTURES)
_COMPILERS = set(conftest.RITZ1_ROW_FIXTURES)


def _const(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _div_parts(node) -> list[str]:
    """`a / "ritz1" / "build"` as its string parts, left to right."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _div_parts(node.left) + _div_parts(node.right)
    s = _const(node)
    return [s] if s is not None else ["?"]


def names_ritz1_binary(tree: ast.AST) -> list[int]:
    """Lines where a module builds or names a path into ritz1/build/."""
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            parts = _div_parts(node)
            if any(a == "ritz1" and b == "build" for a, b in zip(parts, parts[1:])):
                lines.append(node.lineno)
        elif (s := _const(node)) is not None and "ritz1/build" in s and "\n" not in s:
            lines.append(node.lineno)
        elif isinstance(node, ast.Name) and node.id in _PATH_NAMES \
                and isinstance(node.ctx, ast.Load):
            lines.append(node.lineno)
    return sorted(set(lines))


def routes_through_fixture(tree: ast.AST, seen: frozenset = frozenset()) -> bool:
    """Asks for a ritz1 build fixture, or has rows conftest routes to one.

    A fixture is asked for as a parameter, through `getfixturevalue`, or
    with `usefixtures`.  Rows: a list or tuple literal holding a ritz1
    compiler's name (`COMPILERS = ["ritz0", "ritz1", ...]`), which a
    parametrized row carries into conftest item 15, here or in the sibling
    test module it is imported from (`from test_ref_into_value import
    COMPILERS`).
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("test_") \
                and node.module not in seen:
            sibling = RITZ0 / "tests" / f"{node.module}.py"
            if sibling.exists() and routes_through_fixture(
                    ast.parse(sibling.read_text()), seen | {node.module}):
                return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _FIXTURES & {a.arg for a in node.args.args + node.args.kwonlyargs}:
                return True
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name in ("getfixturevalue", "usefixtures") and \
                    _FIXTURES & {_const(a) for a in node.args}:
                return True
        elif isinstance(node, (ast.List, ast.Tuple)):
            if _COMPILERS & {_const(e) for e in node.elts}:
                return True
    return False


def _test_modules() -> list[Path]:
    return sorted(p for p in RITZ0.rglob("test_*.py")
                  if not any(part.startswith(("tmp", "ritz_test_", "ritz_batch_test_"))
                             for part in p.relative_to(RITZ0).parts))


@pytest.mark.unit
def test_every_ritz1_exec_goes_through_its_fixture():
    offenders = []
    for path in _test_modules():
        rel = str(path.relative_to(RITZ0))
        tree = ast.parse(path.read_text(), filename=rel)
        lines = names_ritz1_binary(tree)
        if lines and not routes_through_fixture(tree):
            offenders.append(f"{rel}:{lines[0]}")
    assert not offenders, (
        "these test modules run a ritz1 binary that no fixture built.  Under "
        "xdist that races the build (AGAST #5005).  Ask for `ritz1_bin` (or "
        "`ritz1_selfhosted`), or parametrize the row with the compiler's name "
        "(conftest item 15):\n  " + "\n  ".join(offenders))


@pytest.mark.unit
def test_the_guard_sees_each_spelling():
    """Non-vacuity: each way a module spells the path is seen, and routed."""
    seen = names_ritz1_binary(ast.parse(
        'a = ROOT / "ritz1" / "build" / compiler\n'
        'b = "projects/ritz/ritz1/build/ritz1"\n'
        'c = RITZ1_BUILD / "ritz1"\n'
        '"""ritz1/build/ritz1 in a docstring\nis prose."""\n'))
    assert seen == [1, 2, 3]
    assert not routes_through_fixture(ast.parse('def test_x(tmp_path):\n    run(RITZ1_BIN)\n'))
    for routed in ('def test_x(ritz1_bin):\n    pass\n',
                   'def test_x(request):\n    request.getfixturevalue("ritz1_bin")\n',
                   'pytestmark = pytest.mark.usefixtures("ritz1_selfhosted")\n',
                   'COMPILERS = ["ritz0", "ritz1"]\n'):
        assert routes_through_fixture(ast.parse(routed)), routed


def _item(integration=True, **params):
    marker = object() if integration else None
    item = SimpleNamespace(get_closest_marker=lambda name: marker if name == "integration" else None)
    if params:
        item.callspec = SimpleNamespace(params=params)
    return item


@pytest.mark.unit
@pytest.mark.parametrize("params, fixtures", [
    ({}, []),
    ({"compiler": "ritz0"}, []),
    ({"compiler": "ritz1"}, ["ritz1_bin"]),
    ({"compiler": "ritz1_selfhosted"}, ["ritz1_bin", "ritz1_selfhosted"]),
    ({"site": "let", "comp": "ritz1_selfhosted"}, ["ritz1_bin", "ritz1_selfhosted"]),
    ({"name": "ritz1x", "n": 3}, []),
])
def test_a_ritz1_row_gets_its_compilers_fixtures(params, fixtures):
    assert conftest.ritz1_row_fixtures(_item(**params)) == fixtures


@pytest.mark.unit
def test_a_row_that_runs_nothing_needs_no_ritz1():
    """Not `integration`: it starts no process (item 9), so "ritz1" is a name.

    test_build.py's `[ritz1-resolve.py]` cache rows are smoke; they stay so.
    """
    assert conftest.ritz1_row_fixtures(_item(integration=False, mode="ritz1")) == []


@pytest.mark.integration
def test_a_ritz1_row_fails_when_no_build_ran(tmp_path):
    """The rows that hit EACCES now ask for ritz1: with no build, they fail.

    `--no-ritz1-build` refuses the build verdict (conftest item 14), so a row
    that asks for ritz1 fails naming the option.  Before item 15 the ritz1
    rows of test_array_into_pointer ran the binary on disk and passed.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--disable-plugin-autoload", "-p", "no:cacheprovider",
         "-q", "-rfE", "--no-ritz1-build",
         "tests/test_array_into_pointer.py::test_only_the_pointer_words"],
        cwd=RITZ0, env=dict(os.environ, RITZ_TEST_BATCH="0"),
        capture_output=True, text=True, timeout=600, check=False)
    out = proc.stdout + proc.stderr
    assert re.search(r"\b1 passed\b", out), out[-4000:]          # the ritz0 row
    red = sum(int(n) for n in re.findall(r"(\d+) (?:failed|errors?)\b", out))
    assert red == 2, out[-4000:]                                    # ritz1, ritz1_selfhosted
    assert "--no-ritz1-build" in out, out[-4000:]
