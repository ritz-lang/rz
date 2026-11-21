#!/usr/bin/env python3
"""let/var with a generic enum annotation must resolve the specialization.

AGAST #1321, class 3 (angelo tests.ritz). The shape:

    var opt: Option<Foo> = Some(foo)

The let/var statement path handed the *raw* annotation name (`Option`) to
`_emit_enum_variant_with_type`, which only knows materialized
specializations (`Option$Foo`) -> `ValueError: Unknown enum type: Option`.
The assignment-statement path already resolved the name properly; this
pins the let/var path to the same behaviour.
"""


import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), "--no-runtime"])


GENERIC_ANNOTATED_LET = """\
struct Foo
    n: i32

fn main() -> i32
    var opt: Option<Foo> = Some(Foo { n: 3 })
    match opt
        Some(f) => f.n
        None => 0
"""


def test_var_with_generic_option_annotation(tmp_path):
    """`var opt: Option<Foo> = Some(...)` must compile."""
    result = _compile(tmp_path, GENERIC_ANNOTATED_LET)
    assert result.returncode == 0, (
        f"generic-annotated var binding failed to compile:\n{result.stderr}"
    )


# Guard: non-generic enum annotations took the same branch and worked; they
# must keep working unchanged.
PLAIN_ANNOTATED_LET = """\
enum Color
    Red
    Blue

fn main() -> i32
    var c: Color = Color.Blue
    match c
        Color.Red => 0
        Color.Blue => 1
"""


def test_var_with_plain_enum_annotation(tmp_path):
    result = _compile(tmp_path, PLAIN_ANNOTATED_LET)
    assert result.returncode == 0, (
        f"plain enum annotation guard case failed:\n{result.stderr}"
    )


# AGAST #1964: the `let` path ignored its annotation entirely, so a variant
# constructor took whichever specialization registered last. With both
# Option<f32> and Option<f64> in the module, `let o: Option<f64> = Some(2.5)`
# was built as Option$f32 and the `match` died storing it into an
# Option$f64 slot. Each case pairs the let under test with a later fn that
# registers the competing width.

LET_TWO_WIDTHS = {
    "direct_variant": """\
fn a() -> i64
    let o: Option<f64> = Some(2.5)
    match o
        Some(v) => 1
        None => 0

fn b() -> i64
    let p: Option<f32> = Some(0.5)
    0
""",
    "direct_variant_mirror": """\
fn a() -> i64
    let o: Option<f32> = Some(2.5)
    match o
        Some(v) => 1
        None => 0

fn b() -> Option<f64>
    return Some(0.5)
""",
    "result_ok": """\
fn a() -> i64
    let r: Result<f64, i32> = Ok(2.5)
    match r
        Ok(v) => 1
        Err(e) => 0

fn b() -> i64
    let s: Result<f32, i32> = Ok(0.5)
    0
""",
    "unit_variant": """\
fn a() -> i64
    let o: Option<f64> = None
    match o
        Some(v) => 0
        None => 1

fn b() -> i64
    let p: Option<f32> = Some(0.5)
    0
""",
    # The competing widths are registered *before* `a` so `Some` in the tail
    # does not happen to resolve to Option$f64 by being registered last.
    "if_tail": """\
fn z() -> Option<f64>
    return Some(1.5)

fn y() -> Option<f32>
    return Some(0.5)

fn a(flag: bool) -> i64
    let o: Option<f64> = if flag
        Some(2.5)
    else
        None
    match o
        Some(v) => 1
        None => 0

fn b() -> i64
    let p: Option<f32> = Some(0.5)
    0
""",
}


@pytest.mark.parametrize("case", sorted(LET_TWO_WIDTHS))
def test_let_builds_declared_enum_width(tmp_path, case):
    """`let x: E<T> = <variant>` must build E$T, not the last-registered E."""
    result = _compile(tmp_path, LET_TWO_WIDTHS[case])
    assert result.returncode == 0, (
        f"[{case}] let ignored its declared enum width:\n{result.stderr}"
    )
