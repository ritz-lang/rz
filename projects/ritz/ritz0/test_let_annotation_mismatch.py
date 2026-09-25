#!/usr/bin/env python3
"""`let x: T = expr` must not silently discard an irreconcilable annotation.

AGAST #1364 (the uncontroversial half).

    struct P
        a: i64
        b: i64

    fn mk() -> P
        return P { a: 1, b: 2 }

    fn main() -> i32
        let n: i64 = mk()      # ACCEPTED SILENTLY, before this change
        return n as i32

`_convert_type` ends in a bare `return val` — when it does not know how to
convert, it hands the value back unchanged. LetStmt then records the DECLARED
type against a value that does not have it, so the annotation is discarded and
the eventual error (if any) surfaces a line or two later naming a type the
programmer never wrote. That is why 53_async, 54_async_fs and
55_async_state_machine read as async bugs and sat on the known-failure
allowlist misfiled as "unmigrated async".

ritz0 has no separate type checker — `--check-types` is off by default — so
emission is the first and only pass that could notice.

SCOPE, deliberately narrow. This rejects only the irreconcilable case: a scalar
annotation on an aggregate value, or an aggregate annotation on a scalar value.
Implicit *narrowing* (`let n: i32 = <i64>`) was deliberately left alone here as
an open language question. #1364 has since settled it: it is an error unless
provably lossless (#1393). That rule lives in `_check_implicit_narrowing` and is
tested in test_implicit_narrowing.py; the single test below only marks the flip.

The controls are not padding. `_convert_type` legitimately returns a value
whose LLVM type differs from the target in several cases the compiler depends
on, and a guard that merely compared LLVM types would reject all of them.
"""

import os
import subprocess
import sys
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"

STRUCT_PRELUDE = """\
struct P
    a: i64
    b: i64

fn mk() -> P
    return P { a: 1, b: 2 }

fn five() -> i64
    return 5

"""


def _compile(tmp_path, source, name="unit.ritz"):
    src = tmp_path / name
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


def test_struct_value_into_scalar_annotation_is_rejected(tmp_path):
    r = _compile(tmp_path, STRUCT_PRELUDE + """\
fn main() -> i32
    let n: i64 = mk()
    return n as i32
""")
    assert r.returncode != 0, (
        "`let n: i64 = mk()` compiled; the annotation was discarded\n"
        f"{r.stdout[-1000:]}"
    )


def test_the_rejection_is_located_at_the_let(tmp_path):
    """Naming the line is the entire point — the old failure surfaced later.

    The expected line is derived from the fixture rather than hardcoded, so
    editing the prelude cannot silently turn this into an assertion about the
    wrong line.
    """
    source = STRUCT_PRELUDE + """\
fn main() -> i32
    let n: i64 = mk()
    return n as i32
"""
    lines = source.split("\n")
    let_line = next(i for i, ln in enumerate(lines, 1) if "let n: i64" in ln)
    r = _compile(tmp_path, source)
    assert f"unit.ritz:{let_line}" in r.stderr, (
        f"diagnostic does not point at the let (line {let_line}):\n{r.stderr[-2000:]}"
    )


def test_the_rejection_names_both_types(tmp_path):
    r = _compile(tmp_path, STRUCT_PRELUDE + """\
fn main() -> i32
    let n: i64 = mk()
    return n as i32
""")
    assert "i64" in r.stderr and "P" in r.stderr, (
        f"diagnostic does not name the declared and actual types:\n{r.stderr[-2000:]}"
    )


def test_scalar_value_into_struct_annotation_is_rejected(tmp_path):
    """The mirror image must be caught too, not just one direction."""
    r = _compile(tmp_path, STRUCT_PRELUDE + """\
fn main() -> i32
    let p: P = five()
    return p.a as i32
""")
    assert r.returncode != 0, (
        f"`let p: P = five()` compiled:\n{r.stdout[-1000:]}"
    )


# --- Controls. Each is a conversion _convert_type performs on purpose. ---

def test_matching_scalar_still_compiles(tmp_path):
    r = _compile(tmp_path, STRUCT_PRELUDE + """\
fn main() -> i32
    let n: i64 = five()
    return n as i32
""")
    assert r.returncode == 0, f"a well-typed let was rejected:\n{r.stderr[-2000:]}"


def test_matching_struct_still_compiles(tmp_path):
    r = _compile(tmp_path, STRUCT_PRELUDE + """\
fn main() -> i32
    let q: P = mk()
    return q.a as i32
""")
    assert r.returncode == 0, f"a well-typed let was rejected:\n{r.stderr[-2000:]}"


def test_cstring_literal_into_pointer_still_compiles(tmp_path):
    r = _compile(tmp_path, """\
fn main() -> i32
    let p: *u8 = c"hello"
    return 0
""")
    assert r.returncode == 0, f"`let p: *u8 = c\"..\"` was rejected:\n{r.stderr[-2000:]}"


def test_string_literal_into_strview_still_compiles(tmp_path):
    """StrView is an aggregate and the literal lowers to one — must not trip."""
    r = _compile(tmp_path, """\
fn main() -> i32
    let s: StrView = "hello"
    return 0
""")
    assert r.returncode == 0, f"`let s: StrView = \"..\"` was rejected:\n{r.stderr[-2000:]}"


def test_integer_literal_into_sized_scalar_still_compiles(tmp_path):
    r = _compile(tmp_path, """\
fn main() -> i32
    let a: i32 = 7
    let b: u8 = 3
    let c: f64 = 1.5
    return a
""")
    assert r.returncode == 0, f"a literal-initialised let was rejected:\n{r.stderr[-2000:]}"


def test_address_of_into_pointer_still_compiles(tmp_path):
    r = _compile(tmp_path, STRUCT_PRELUDE + """\
fn main() -> i32
    var q = mk()
    let p: *P = @q
    return p.a as i32
""")
    assert r.returncode == 0, f"`let p: *P = @q` was rejected:\n{r.stderr[-2000:]}"


def test_implicit_narrowing_is_rejected(tmp_path):
    """Flipped on purpose — this is not a regression.

    This test used to be `test_implicit_narrowing_is_still_accepted`, a marker
    pinning the old silent truncation while #1364 was undecided. The user
    settled #1364 on 2026-09-09 (narrowing is an error, explicit `as T`
    required) and refined it on 2026-09-24 to exempt provably lossless
    constants and masks (#1393). `five()` returns an i64 the compiler cannot
    bound, so it must now be rejected. The full rule is tested in
    test_implicit_narrowing.py.
    """
    r = _compile(tmp_path, STRUCT_PRELUDE + """\
fn main() -> i32
    let n: i32 = five()
    return n
""")
    assert r.returncode != 0, "`let n: i32 = five()` (i64) compiled; #1393 makes it an error"
    assert "implicit narrowing" in r.stderr, r.stderr[-2000:]
