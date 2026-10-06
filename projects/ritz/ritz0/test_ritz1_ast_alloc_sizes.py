"""Regression tests for AGAST #1649: ritz1 must allocate whole AST nodes.

`monomorph.ritz` cloned every statement of every generic fn body into
`malloc(160)` although `Stmt` is 192 bytes, and cloned expressions into
`malloc(160)` / `malloc(96)` (the `sizeof(T)` argument), so cloning wrote
past the end of the block.  The parser allocated `Expr` nodes with
`parser_alloc(p, 120)` although `Expr` is 128 bytes.  The clones also never
copied `span`, so a diagnostic inside an instantiated generic body named
whatever line number happened to be in the uninitialised memory.

The fix spells every Stmt/Expr allocation as `sizeof(Stmt)` / `sizeof(Expr)`
and copies `span` in `clone_stmt` / `clone_expr`.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_SRC = RITZ_ROOT / "ritz1" / "src"
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

# A Stmt/Expr allocation whose size is an integer literal, e.g.
# `malloc(160) as *Stmt` or `parser_alloc(p, 120) as *Expr`.
LITERAL_ALLOC = re.compile(
    r"\b(?:malloc|parser_alloc)\(\s*(?:\w+\s*,\s*)?\d+\s*\)\s+as\s+\*(Stmt|Expr)\b"
)


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; a stale binary would test the old code."""
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the AST alloc-size tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    return RITZ1_BIN


def _fn_body(src: str, name: str) -> str:
    """Return the text of top-level `fn name(...)` up to the next top-level item."""
    m = re.search(rf"^fn {name}\(.*?(?=^\S)", src, re.S | re.M)
    assert m, f"fn {name} not found"
    return m.group(0)


# ---------------------------------------------------------------------------
# Static gates
# ---------------------------------------------------------------------------


def test_no_literal_sized_stmt_or_expr_allocs():
    """Every Stmt/Expr allocation in ritz1 must be sized with sizeof()."""
    offenders = []
    for path in sorted(RITZ1_SRC.glob("*.ritz")):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if LITERAL_ALLOC.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Stmt/Expr allocated with a literal size (use sizeof(Stmt)/sizeof(Expr)):\n"
        + "\n".join(offenders)
    )


def test_clone_stmt_copies_span():
    """A cloned statement keeps its source position."""
    body = _fn_body((RITZ1_SRC / "monomorph.ritz").read_text(), "clone_stmt")
    assert re.search(r"^\s*cloned\.span\s*=\s*s\.span\b", body, re.M), (
        "clone_stmt does not copy s.span into the clone"
    )


def test_clone_expr_copies_span():
    """A cloned expression keeps its source position (static half)."""
    body = _fn_body((RITZ1_SRC / "monomorph.ritz").read_text(), "clone_expr")
    assert re.search(r"^\s*cloned\.span\s*=\s*e\.span\b", body, re.M), (
        "clone_expr does not copy e.span into the clone"
    )


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

# The c"..." placeholder is on line 6; the error is only reported for the
# instantiated (cloned) body, so the line it names comes from the clone.
SPAN_PROGRAM = """\
fn ident<T>(x: T) -> T
    let y: T = x



    print(c"bad {y}\\n")
    return y

fn main() -> i32
    let a: i32 = ident<i32>(3)
    return 0
"""


def test_generic_body_diagnostic_names_source_line(ritz1_bin, tmp_path):
    src = tmp_path / "span.ritz"
    src.write_text(SPAN_PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(tmp_path / "span.ll")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode != 0, "ritz1 accepted an interpolating c-string"
    m = re.search(r"cannot emit: line (-?\d+):", proc.stderr)
    assert m, proc.stderr[-2000:]
    assert m.group(1) == "6", (
        f"diagnostic in a cloned generic body names line {m.group(1)}, not 6:\n"
        + proc.stderr[-2000:]
    )


# Exercises every clone_stmt kind that touches the tail of Stmt
# (for_end/for_body/expr/next) plus a sizeof(T) argument rewrite.
OVERFLOW_PROGRAM = """\
fn work<T>(x: T) -> T
    var acc: T = x
    for i in 0..3
        acc = acc + x
    while acc > x
        acc = acc - x
    if acc == x
        acc = acc + 0
    let n: i64 = sizeof(T)
    print("{n}\\n")
    return acc

fn main() -> i32
    let a: i32 = work<i32>(3)
    let b: i64 = work<i64>(4)
    return 0
"""


@pytest.mark.skipif(shutil.which("valgrind") is None, reason="valgrind not installed")
def test_monomorph_clone_writes_stay_in_bounds(ritz1_bin, tmp_path):
    src = tmp_path / "ovf.ritz"
    src.write_text(OVERFLOW_PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    proc = subprocess.run(
        ["valgrind", "-q", str(ritz1_bin), str(src), "-o", str(tmp_path / "ovf.ll")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    err = proc.stderr
    assert "Invalid write" not in err and "Heap block lo/hi size mismatch" not in err, (
        "ritz1 wrote out of bounds while monomorphizing:\n" + err[-4000:]
    )
    assert proc.returncode == 0, err[-4000:]
