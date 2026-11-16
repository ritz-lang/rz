#!/usr/bin/env python3
"""The stack smoke gate stays a package of small, flat modules (AGAST #3455).

LARB review/5 (tooling.md F3) found tools/smoke_stack.py at 1,599 lines,
its suite_stack 359 SLOC / CC 110 / depth 11: ~25 nested closures sharing
the stack's processes and ports through captured locals. It is now one
module per suite under tools/smoke_stack/, the shared state is a ctx
dataclass, and every check is a module-level function taking it.

These pin the ticket's acceptance thresholds with the metric the review
used (projects/larb/tools/ritz-metrics, stdlib only), so the package can't
regrow the shape the review flagged:

  * no file over 600 lines;
  * no function over 80 SLOC or cyclomatic complexity 20;
  * no nested def anywhere (not only the review's `^\\s{8,}def ` grep:
    a def nested at any depth is a closure sharing captured state).

Run with:
    python3 -m pytest projects/ritz/tools/test_smoke_stack_shape.py -q
"""

from __future__ import annotations

import ast
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PKG = HERE / "smoke_stack"
METRICS = HERE.parents[2] / "projects" / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"

MAX_FILE_LINES = 600
MAX_FN_SLOC = 80
MAX_FN_CC = 20


def _metrics():
    spec = importlib.util.spec_from_file_location("ritz_metrics_3455", METRICS)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # @dataclass looks its module up there
    spec.loader.exec_module(mod)
    return mod


def _sources() -> list[Path]:
    files = sorted(PKG.glob("*.py"))
    assert len(files) >= 5, f"{PKG} is not the per-suite package (found {len(files)} files)"
    return files


@pytest.mark.unit
def test_the_monolith_is_gone():
    # A smoke_stack.py beside the smoke_stack/ package would also be shadowed
    # by it on import: two sources for one name.
    assert not (HERE / "smoke_stack.py").exists()
    assert (PKG / "__init__.py").is_file() and (PKG / "__main__.py").is_file()


@pytest.mark.unit
@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_no_package_file_is_git_ignored():
    # The root .gitignore's core-dump rule `core.*` once swallowed a
    # smoke_stack/core.py: the gate passed on the untracked file in the
    # worktree, and the commit failed to import everywhere else.
    names = [p.name for p in PKG.glob("*.py")]
    r = subprocess.run(["git", "check-ignore", "-v", *names], cwd=PKG,
                       capture_output=True, text=True, check=False)
    if r.returncode == 128:
        pytest.skip(f"not a git checkout: {r.stderr.strip()}")
    assert r.returncode == 1, f"git ignores package files:\n{r.stdout}"


@pytest.mark.unit
def test_no_file_over_600_lines():
    long = {p.name: n for p in _sources() if (n := len(p.read_text().splitlines())) > MAX_FILE_LINES}
    assert not long, f"over {MAX_FILE_LINES} lines: {long}"


@pytest.mark.unit
def test_no_function_over_80_sloc_or_cc_20():
    m = _metrics()
    bad = []
    for p in _sources():
        for fn in m.extract_functions(p, p.read_text().splitlines(), "py"):
            if fn.sloc > MAX_FN_SLOC or fn.complexity > MAX_FN_CC:
                bad.append(f"{p.name}:{fn.line} {fn.name} sloc={fn.sloc} cc={fn.complexity}")
    assert not bad, "\n".join(bad)


@pytest.mark.unit
def test_no_nested_def():
    grep = [f"{p.name}:{i}" for p in _sources()
            for i, ln in enumerate(p.read_text().splitlines(), 1) if re.match(r"^\s{8,}def ", ln)]
    assert not grep, f"the review's grep `^\\s{{8,}}def ` matches: {grep}"
    nested = []
    for p in _sources():
        for outer in ast.walk(ast.parse(p.read_text())):
            if not isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for inner in ast.walk(outer):
                if inner is not outer and isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nested.append(f"{p.name}:{inner.lineno} {inner.name} in {outer.name}")
    assert not nested, f"nested defs (closures over captured state): {nested}"


@pytest.mark.unit
def test_the_metrics_flag_a_closure_and_a_long_function(tmp_path):
    """A floor never observed failing is no floor: the same metric that
    passes the package flags the shape the review found."""
    src = ["def suite(r):", "    x = 1", "    def check():", "        return x"]
    src += [f"    if x == {i}:\n        x += 1" for i in range(MAX_FN_CC)]
    f = tmp_path / "bad.py"
    f.write_text("\n".join(src) + "\n")
    fns = {fn.name: fn for fn in _metrics().extract_functions(f, f.read_text().splitlines(), "py")}
    assert fns["suite"].complexity > MAX_FN_CC
    assert any(isinstance(n, ast.FunctionDef) and n.name == "check"
               for n in ast.walk(ast.parse(f.read_text()).body[0]))
