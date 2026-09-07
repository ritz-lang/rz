"""Regression tests for AGAST #1361 — ritz1 must scale pointer arithmetic
when the pointer operand is itself a binary expression.

`emit_expr_arith` decides "is this pointer arithmetic?" by inspecting the
SHAPE of the left operand: EXPR_IDENT (`p + i`) or EXPR_MEMBER (`s.ptr + i`).
An unparenthesised chain parses left-associatively:

    lines.data + i - 1   ==   SUB( ADD( MEMBER(lines,data), i ), 1 )

The outer SUB's left operand is EXPR_BINARY, which matches neither arm, so
`is_ptr_arith` stays 0 and the `- 1` is emitted as a raw byte subtraction.
For a 16-byte element that lands 15 bytes short of the intended element and
every subsequent field load reads across the element boundary.

This is NOT a crash. It silently computes a wrong address, which is how it
survived: `tier2_stdlib/14_uniq` does exactly `lines.data + i - 1` to reach
the previous line, so `prev` was misaligned, `lines_equal` never returned 1,
no group ever formed, and `uniq` passed every line through unchanged. The
differential stages diff *bare-run* output, and bare `uniq` with no stdin
prints nothing under all three compilers — so they "agreed" and the suite
was green.

Both directions are pinned below:

  * the chain must produce the SAME answer as the parenthesised form, and
  * the parenthesised form must keep working (it is the arm that was
    already correct — a fix that breaks it has moved the bug, not fixed it).

The assertions are on the *runtime exit code*, not on emitted IR text. An
IR-shape assertion would pass against any emitter that merely emits a `mul`
somewhere; only running the binary proves the address is right. Element 0
holds 10 and element 1 holds 20, so a misaligned read yields 0 — distinct
from both, and distinct from the exit code of a crash.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# ritz1 compiles to a module with `main`; `_start` comes from this runtime
# object, exactly as build.py links it. Linking WITHOUT it "works" (ld
# defaults the entry point to 0x1000) and then segfaults — which would make
# every case here fail for a reason that has nothing to do with #1361.
#
# It is a BUILD PRODUCT, not a tracked file: runtime/.gitignore ignores *.o
# and only the .ll sources are committed. An earlier version of this file
# asserted the .o existed and told the reader to run `make -C runtime`. That
# passes on any developer machine that has ever built and fails on a fresh
# checkout — which is exactly how it broke main CI (bootstrap/"ritz0 unit
# tests", run ebb5a48). Note also that ritz1's own Makefile links
# ritz_start_ENVP.x86_64.o, so building ritz1 does not incidentally produce
# this one. So build it, the same way ritz1/Makefile's ../runtime/%.o rule
# does: delegate to runtime/Makefile and let make decide whether to do work.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; make's dependency graph decides what to do.

    Same rationale as test_ritz1_parse_errors.py: a stale binary asserts
    nothing just as effectively as a missing one, and this test's whole
    purpose is to detect a change in ritz1's emitter.
    """
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
            "could not build ritz1 for the pointer-arithmetic regression tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    """Bring RITZ_START up to date. See the RITZ_START comment for why this
    builds rather than asserts: the .o is gitignored, so asserting is a test
    that only ever passes on a machine that has already built something else.
    """
    proc = subprocess.run(
        ["make", "-C", "runtime", RITZ_START.name],
        cwd=RITZ_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0 or not RITZ_START.exists():
        pytest.fail(
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    _build_runtime_start()
    return RITZ1_BIN


# Two 16-byte elements. `base` points at element 0 (start=10), `base + 1` at
# element 1 (start=20). With i == 1, `base + i - 1` must land back on element
# 0 and return 10.
PROGRAM = """\
struct LB
    start: i64
    fin: i64

fn main() -> i32
    var arr: [2]LB
    let base: *LB = @arr[0]
    base.start = 10
    base.fin = 11
    let one: *LB = base + 1
    one.start = 20
    one.fin = 21
    let i: i64 = 1
    let q: *LB = %s
    return q.start as i32
"""

CHAIN = "base + i - 1"
PARENS = "base + (i - 1)"


def _run(compiler: str, tmp_path: Path, offset_expr: str) -> int:
    """Compile PROGRAM with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"case_{compiler}.ritz"
    src.write_text(PROGRAM % offset_expr)
    ll = tmp_path / f"case_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))

    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    comp = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile `{offset_expr}`:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )

    exe = tmp_path / f"case_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        assert RITZ_START.exists(), (
            f"runtime start object missing: {RITZ_START} — run `make -C runtime`"
        )
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for `{offset_expr}`:\n"
        f"{link.stderr[-2000:]}"
    )

    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
def test_ritz0_chain_is_correct(tmp_path):
    """The reference answer. If this ever changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, CHAIN) == 10


@pytest.mark.integration
def test_ritz1_unparenthesised_chain_scales_by_element_size(ritz1_bin, tmp_path):
    """AGAST #1361: `base + i - 1` on a 16-byte element type.

    Before the fix this returned 0 — the `- 1` was applied as one BYTE, so
    `q` pointed 15 bytes into element 0's padding and `q.start` read garbage
    that happened to be zero. 0 is distinct from element 0's 10 and element
    1's 20, so this assertion cannot be satisfied by landing on the wrong
    element either.
    """
    assert _run("ritz1", tmp_path, CHAIN) == 10


@pytest.mark.integration
def test_ritz1_parenthesised_form_still_correct(ritz1_bin, tmp_path):
    """The arm that already worked. A fix that regresses this moved the bug."""
    assert _run("ritz1", tmp_path, PARENS) == 10


@pytest.mark.integration
def test_ritz0_and_ritz1_agree_on_the_chain(ritz1_bin, tmp_path):
    """Parity, stated directly.

    The differential regression stages compare ritz0 and ritz1 output, and
    they did NOT catch this — they diff a bare run of `uniq`, which prints
    nothing under either compiler. This asserts the parity that the corpus
    diff was believed to be asserting.
    """
    r0 = _run("ritz0", tmp_path, CHAIN)
    r1 = _run("ritz1", tmp_path, CHAIN)
    assert r0 == r1, f"ritz0 returned {r0}, ritz1 returned {r1} for `{CHAIN}`"
