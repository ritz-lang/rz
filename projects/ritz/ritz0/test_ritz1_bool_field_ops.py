"""Regression tests for AGAST #1646 (and #1648): operators, returns and call
args over bool struct fields and bool params under ritz1.

ritz1's value model keeps every scalar in an i64 register; i1 appears only at
ABI edges (call args, `ret`, field stores) and at `br`. Bool locals (#1521's
emit_var_decl), bool params (#1497) and bool call results already follow it.
A bool struct FIELD load did not: emit_expr_member handed back the raw
`load i1`, and every i64 consumer then emitted invalid IR:

    not g.b        -> icmp eq i64 %i1, 0
    g.b and t.b    -> icmp ne i64 %i1, 0
    g.b == false   -> icmp eq i64 %i1, 0
    -> bool  g.b   -> trunc i64 %i1 to i1      (ritzlib/argspec, 77_args)

The call-arg coercion had the inverse bug: it treated every TYPE_BOOL arg as
already i1, so `takes(yes())` passed the zext'd i64 of a bool call to an i1
param.

Each program returns 42 when correct and a distinct small code naming the
check that failed otherwise. ritz0 is the oracle; everything runs at RUNTIME.
Every operator is exercised both as a condition and as a value, and with
both truth values, so a constant-folded or inverted lowering cannot pass.
"""

import pytest

from test_ritz1_bool_fields import EXPECTED, _run, ritz1_bin  # noqa: F401, F811

STRUCTS = """\
struct G
    b: bool
    c: i32

struct H
    g: G
    d: bool

"""

PROGRAMS = {
    # The ticket repro, plus `not` as a value, through a pointer and nested.
    "not_field": STRUCTS
    + """\
pub fn main() -> i32
    let t = G { c: 5, b: true }
    let f = G { c: 6, b: false }
    if not t.b
        return 1
    if not f.b
        let p: *G = @t
        if not p.b
            return 3
        let nt: bool = not t.b
        let nf = not f.b
        if nt
            return 4
        if not nf
            return 5
        let gi = G { b: false, c: 1 }
        let h = H { g: gi, d: true }
        if not h.g.b
            if not h.d
                return 6
            while not f.b
                return 42
            return 7
        return 8
    return 2
""",
    # Comparisons of a bool field against a literal, a field and a local.
    "eq_field": STRUCTS
    + """\
pub fn main() -> i32
    let t = G { c: 5, b: true }
    let f = G { c: 6, b: false }
    if t.b == false
        return 1
    if f.b != false
        return 2
    if t.b == f.b
        return 3
    let x: bool = true
    if t.b != x
        return 4
    let e1: bool = f.b == false
    let e2 = t.b == f.b
    if not e1
        return 5
    if e2
        return 6
    if t.b == true
        return 42
    return 7
""",
    # `and` over two fields / field and local, every truth combination.
    "and_field": STRUCTS
    + """\
fn chk(a: @G, b: @G) -> i32
    let v: bool = a.b and b.b
    var r: i32 = 0
    if a.b and b.b
        r = 1
    if v
        r = r + 2
    r

pub fn main() -> i32
    let t = G { c: 5, b: true }
    let f = G { c: 6, b: false }
    if chk(@t, @t) != 3
        return 1
    if chk(@t, @f) != 0
        return 2
    if chk(@f, @t) != 0
        return 3
    if chk(@f, @f) != 0
        return 4
    let x: bool = true
    if t.b and not x
        return 5
    if x and f.b
        return 6
    return 42
""",
    # `or` with a field on either side and a local / comparison on the other.
    "or_field": STRUCTS
    + """\
fn chk(a: @G, x: bool) -> i32
    let v: bool = a.b or x
    let w = x or a.b
    var r: i32 = 0
    if a.b or x
        r = 1
    if v
        r = r + 2
    if w
        r = r + 4
    r

pub fn main() -> i32
    let t = G { c: 5, b: true }
    let f = G { c: 6, b: false }
    if chk(@t, false) != 7
        return 1
    if chk(@f, true) != 7
        return 2
    if chk(@f, false) != 0
        return 3
    if f.b or f.c > 9
        return 4
    if f.b or t.b
        return 42
    return 5
""",
    # `-> bool` returning a field: tail and `return`, by ref, by value, nested,
    # and an operator over a field. ritzlib/argspec's flag_takes_value shape.
    "return_field": STRUCTS
    + """\
fn tail_ref(g: @G) -> bool
    g.b

fn ret_ref(g: @G) -> bool
    return g.b

fn tail_val(g: G) -> bool
    g.b

fn ret_nested(h: @H) -> bool
    return h.g.b

fn tail_not(g: @G) -> bool
    not g.b

fn ret_and(g: @G, h: @H) -> bool
    return g.b and h.d

pub fn main() -> i32
    let t = G { c: 5, b: true }
    let f = G { c: 6, b: false }
    if not tail_ref(@t)
        return 1
    if tail_ref(@f)
        return 2
    if not ret_ref(@t)
        return 3
    if ret_ref(@f)
        return 4
    let vt = G { c: 1, b: true }
    let vf = G { c: 2, b: false }
    if not tail_val(vt)
        return 5
    if tail_val(vf)
        return 6
    let gi = G { c: 3, b: true }
    let h = H { g: gi, d: false }
    if not ret_nested(@h)
        return 7
    if tail_not(@t)
        return 8
    if not tail_not(@f)
        return 9
    if ret_and(@t, @h)
        return 10
    let v: bool = ret_ref(@t)
    if v
        return 42
    return 11
""",
    # Field values flowing into bool params, locals and other fields;
    # plus a bool-returning call passed straight to a bool param.
    "field_flows": STRUCTS
    + """\
fn takes(x: bool) -> i32
    if x
        return 1
    0

fn yes() -> bool
    true

pub fn main() -> i32
    var t = G { c: 5, b: true }
    var f = G { c: 6, b: false }
    if takes(t.b) != 1
        return 1
    if takes(f.b) != 0
        return 2
    if takes(not f.b) != 1
        return 3
    if takes(yes()) != 1
        return 4
    if takes(t.b and f.b) != 0
        return 5
    let l = t.b
    if not l
        return 6
    f.b = t.b
    if f.c != 6
        return 7
    if not f.b
        return 8
    t.b = not t.b
    if t.b
        return 9
    if f.b and not t.b
        return 42
    return 10
""",
    # AGAST #1648: the same operators on bool PARAMETERS.
    "param_ops": """\
fn neg(flag: bool) -> i64
    if not flag
        return 1
    return 0

fn andp(flag: bool, n: i64) -> i64
    let r: bool = flag and n > 1
    if r
        return 1
    return 0

fn orp(flag: bool, n: i64) -> bool
    flag or n > 1

pub fn main() -> i32
    if neg(true) != 0
        return 1
    if neg(false) != 1
        return 2
    if andp(true, 5) != 1
        return 3
    if andp(false, 5) != 0
        return 4
    if andp(true, 0) != 0
        return 5
    if not orp(false, 5)
        return 6
    if orp(false, 0)
        return 7
    if not orp(true, 0)
        return 8
    return 42
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_bool_field_ops(ritz1_bin, tmp_path, name):  # noqa: F811
    """ritz1 fed i1 bool-field loads to i64 operators (#1646, #1648)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
