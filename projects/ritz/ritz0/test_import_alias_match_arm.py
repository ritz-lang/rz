#!/usr/bin/env python3
"""An `import M as A` alias must not crash on a single-expression match arm.

Found by AGAST #1472. ImportResolver rewrites `A.f(...)` to `f(...)` in every
module a program with an alias import reaches, and it walked each match arm's
body with _transform_block, which assumes a Block. A body such as `Some(_) => 1`
is an IntLit, so ritz0 died with

    AttributeError: 'IntLit' object has no attribute 'stmts'

before emitting anything. ritzlib/option.ritz is written in that style, so
`import ritzlib.sys as sys` plus anything that reaches ritzlib.option (after
#1472 that includes ritzlib.io, through strview) failed to compile.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
BUILD_PY = RITZ_ROOT / "build.py"


def _run(tmp_path: Path, source: str) -> subprocess.CompletedProcess:
    src = tmp_path / "main.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [sys.executable, str(BUILD_PY), "run", str(src)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )


@pytest.mark.integration
def test_alias_import_with_expression_arms_in_an_imported_module(tmp_path):
    # option.ritz's option_is_some is `Some(_) => 1` / `None => 0`.
    result = _run(tmp_path, (
        "import ritzlib.sys as sys\n"
        "import ritzlib.option\n"
        "\n"
        "fn main() -> i32\n"
        "    let o: Option<i32> = Some(5)\n"
        "    option_is_some<i32>(@o) + 6\n"
    ))
    assert "has no attribute 'stmts'" not in result.stderr + result.stdout
    assert result.returncode == 7, result.stderr + result.stdout


@pytest.mark.integration
def test_alias_call_inside_an_expression_arm_is_resolved(tmp_path):
    # `s::isdigit(c) + 10` is an expression arm calling through the alias: it
    # must be rewritten to `isdigit`, not merely left alone.
    result = _run(tmp_path, (
        "import ritzlib.str as s\n"
        "\n"
        "fn main() -> i32\n"
        "    let c: u8 = 55\n"
        "    match c\n"
        "        55 => s::isdigit(c) + 10\n"
        "        _ => 20\n"
    ))
    assert result.returncode == 11, result.stderr + result.stdout
