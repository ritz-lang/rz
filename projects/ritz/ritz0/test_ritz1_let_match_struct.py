"""AGAST #1666: an untyped `let v = match ...` over struct-valued arms.

THE DEFECT

emit_var_decl (ritz1/src/emitter_stmt.ritz) sizes an unannotated local's slot
from its initializer *before* emitting it, and had no EXPR_MATCH case. The
#1645 merge phi of a struct-valued match is `%StrView` / `%Point`, but the
slot kept the parser default TYPE_I64, so ritz1 emitted `alloca i64` +
`store i64 <%StrView phi>` and clang rejected the IR:

    fn first(o: Option<StrView>, d: StrView) -> StrView
        let v = match o
            Some(s) => s
            None => d
        return v

("'%.17' defined with type '%StrView' but expected 'i64'").  The annotated
`let v: StrView = match o ...` already worked.

THE FIX

For an untyped EXPR_MATCH initializer, the match is emitted first and the
local takes the phi's aggregate type (MatchResult.agg_name, exposed by
emit_match), so the slot is `alloca %StrView` and `.field` access resolves.
A scalar match still binds an i64.

Oracle: ritz0 builds and runs every program with the same exit code.  Each
program returns 42 when correct and a small code naming the failed check.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# The ticket's repro: bound arm first, StrView param second.
BOUND_THEN_PARAM = """\
import ritzlib.strview

fn first(o: Option<StrView>, d: StrView) -> StrView
    let v = match o
        Some(s) => s
        None => d
    return v

pub fn main() -> i32
    let a = first(Some("Seven"), "zz")
    if a.len != 5 or *a.ptr != 83
        return 1
    let b = first(None, "zz")
    if b.len != 2 or *b.ptr != 122
        return 2
    return 42
"""

# The other arm order: param first, bound second.
PARAM_THEN_BOUND = """\
import ritzlib.strview

fn first(o: Option<StrView>, d: StrView) -> StrView
    let v = match o
        None => d
        Some(s) => s
    return v

pub fn main() -> i32
    let a = first(Some("Seven"), "zz")
    if a.len != 5 or *a.ptr != 83
        return 1
    let b = first(None, "zz")
    if b.len != 2 or *b.ptr != 122
        return 2
    return 42
"""

# A `"..."` arm second (#1662's literal lowering is %Span$u8; phi is StrView).
# `v.len` is read off the local itself, so it must be registered as a struct.
BOUND_THEN_LITERAL = """\
import ritzlib.strview

fn or_none(o: Option<StrView>) -> StrView
    let v = match o
        Some(s) => s
        None => "(none)"
    if v.len == 0
        return v
    return v

pub fn main() -> i32
    let a = or_none(Some("Seven"))
    if a.len != 5 or *a.ptr != 83
        return 1
    let b = or_none(None)
    if b.len != 6 or *b.ptr != 40
        return 2
    return 42
"""

# A `"..."` arm first: the literal arm fixes the phi as StrView.
LITERAL_THEN_BOUND = """\
import ritzlib.strview

fn or_none(o: Option<StrView>) -> i64
    let v = match o
        None => "(none)"
        Some(s) => s
    return v.len

pub fn main() -> i32
    if or_none(Some("Seven")) != 5
        return 1
    if or_none(None) != 6
        return 2
    return 42
"""

# A user struct payload, `var` spelling, then a field store through the local.
USER_STRUCT_VAR = """\
struct Point
    x: i64
    y: i64

fn pick(o: Option<Point>) -> i64
    var p = match o
        Some(q) => q
        None => Point { x: 1, y: 2 }
    p.y = p.y + 100
    return p.x * 1000 + p.y

pub fn main() -> i32
    if pick(Some(Point { x: 3, y: 4 })) != 3104
        return 1
    if pick(None) != 1102
        return 2
    return 42
"""

# A scalar match must still bind an i64 (no regression).
SCALAR_MATCH = """\
fn val(o: Option<i64>) -> i64
    let n = match o
        Some(x) => x
        None => 0
    return n + 1

pub fn main() -> i32
    if val(Some(40)) != 41
        return 1
    if val(None) != 1
        return 2
    return 42
"""

CASES = {
    "bound_then_param": (BOUND_THEN_PARAM, 42),
    "param_then_bound": (PARAM_THEN_BOUND, 42),
    "bound_then_literal": (BOUND_THEN_LITERAL, 42),
    "literal_then_bound": (LITERAL_THEN_BOUND, 42),
    "user_struct_var": (USER_STRUCT_VAR, 42),
    "scalar_match": (SCALAR_MATCH, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_let_match_struct(ritz1_bin, tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want
