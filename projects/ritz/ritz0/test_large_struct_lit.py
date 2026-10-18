"""AGAST #1741: ritz0 builds a large struct LITERAL in memory, not first-class.

THE DEFECT

ritz0's `_emit_struct_lit` built every struct literal as a first-class value:

    %a = insertvalue %Big undef, [128 x %Row] %rows, 0
    %b = insertvalue %Big %a, i32 0, 1
    store %Big %b, ptr %dst            ; or the sret slot

#1732's copy rewrite does not catch it (the stored value is an insertvalue,
not a load).  For the 22 KB shape of tokens.ritz's %TokenDefs, clang -O2
times out once the constructor is live (pub, or called).  ritz1 already
builds literals in place (emit_struct_lit_to_alloca).

THE FIX

A literal of a named struct of at least SRET_MIN_BYTES (256) is built
field-by-field into an entry-block slot: one GEP + store per field, a large
array-fill field filled in place, a nested large literal built recursively
into its field, and a missing field zeroed (memset when large).  The literal
then yields `load %T, slot`, which every consumer already turns into an sret
store / #1732 pointer-to-pointer copy / byval pointer, so no first-class
large %T is ever stored, inserted into, or returned.

Every clang -O2 run is bounded (see test_ritz1_large_struct_ret._clang_bounded).
"""

import re

import pytest

from test_ritz1_builtin_struct_shadow import ritz1_bin  # noqa: F401
from test_ritz1_large_struct_ret import (
    _assert_no_libc_mem,
    _link_run,
    _o2_object,
    _ritz0_ll,
    _ritz1_ll,
)

DECLS = """\
struct Row
    id: i32
    name: [32]u8
    pat: [128]u8
    a: i32
    b: i32

struct Big
    rows: [{n}]Row
    count: i32

struct Outer
    tag: i32
    big: Big

extern fn sink(p: *Big) -> i32
extern fn sink_v(b: Big) -> i32
extern fn sink_o(p: *Outer) -> i32
extern fn big_ext() -> Big
"""

HUGE = DECLS.format(n=128)

ROW = "Row { id: 0, name: [0; 32], pat: [0; 128], a: 0, b: 0 }"
ROW_SET = "Row { id: 1, name: [7; 32], pat: [0; 128], a: 2, b: 3 }"

# Each case puts a 22 KB literal in a LIVE (pub) function.
LIT_CASES = {
    "return_lit": f"""
pub fn big_new() -> Big
    return Big {{ rows: [{ROW}; 128], count: 0 }}
""",
    "return_lit_nonzero_rows": f"""
pub fn big_new(c: i32) -> Big
    return Big {{ rows: [{ROW_SET}; 128], count: c }}
""",
    "var_init_lit": f"""
pub fn use1() -> i32
    var b: Big = Big {{ rows: [{ROW}; 128], count: 4 }}
    return sink(@b)
""",
    "let_init_lit": f"""
pub fn use1() -> i32
    let b = Big {{ rows: [{ROW}; 128], count: 4 }}
    return b.count
""",
    "assign_lit": f"""
pub fn use1(p: *Big) -> i32
    var b: Big = *p
    b = Big {{ rows: [{ROW}; 128], count: 4 }}
    return sink(@b)
""",
    "byval_arg_lit": f"""
pub fn use1() -> i32
    return sink_v(Big {{ rows: [{ROW}; 128], count: 4 }})
""",
    "nested_lit": f"""
pub fn use1() -> i32
    var o: Outer = Outer {{ tag: 1, big: Big {{ rows: [{ROW}; 128], count: 4 }} }}
    return sink_o(@o)
""",
    "missing_field_lit": """
pub fn big_new() -> Big
    return Big { count: 9 }
""",
    "field_from_sret_call": """
pub fn use1() -> i32
    var o: Outer = Outer { tag: 1, big: big_ext() }
    return sink_o(@o)
""",
    "field_from_deref": """
pub fn use1(p: *Big) -> i32
    var o: Outer = Outer { tag: 1, big: *p }
    return sink_o(@o)
""",
}

# `insertvalue %"struct.m.Big" ...` / `store %"struct.m.Big" %v` (and the
# same for Outer); a `store %"struct.m.Big"* ...` pointer store is fine.
# Also a first-class store of the 22 KB `[128 x %Row]` field (e.g. an omitted
# field zeroed with `store [128 x %Row] zeroinitializer` instead of memset).
FIRST_CLASS = re.compile(
    r'(insertvalue|store) (%"?[\w.]*(Big|Outer)"?|\[128 x %"?[\w.]*Row"?\]) ')


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LIT_CASES))
def test_huge_struct_lit_compiles_at_O2_within_bound(tmp_path, name):
    ll = _ritz0_ll(tmp_path, name, HUGE + LIT_CASES[name])
    _assert_no_libc_mem(_o2_object(ll))


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LIT_CASES))
def test_huge_struct_lit_has_no_first_class_aggregate(tmp_path, name):
    """No insertvalue into, and no first-class store of, a large struct."""
    text = _ritz0_ll(tmp_path, name, HUGE + LIT_CASES[name]).read_text()
    bad = [ln.strip() for ln in text.splitlines() if FIRST_CLASS.search(ln)]
    assert not bad, f"first-class large-struct values survive: {bad[:5]}"


# __ritz_sret_copy calls each case may emit.  0 = the literal is built in
# its final home: the sret slot, the new var, the byval temp, or the field of
# an enclosing literal (an sret call writes that field directly).
EXPECTED_COPIES = {
    "return_lit": 0,
    "return_lit_nonzero_rows": 0,
    "var_init_lit": 0,
    "let_init_lit": 0,
    "byval_arg_lit": 0,
    "nested_lit": 0,
    "missing_field_lit": 0,
    "field_from_sret_call": 0,
    # `var b: Big = *p`, then the assigned literal's temp into b.
    "assign_lit": 2,
    # *p into o.big.
    "field_from_deref": 1,
}

COPY_CALL = re.compile(r'call void @"?__ritz_sret_copy"?\(')


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LIT_CASES))
def test_huge_struct_lit_is_built_in_place(tmp_path, name):
    text = _ritz0_ll(tmp_path, name, HUGE + LIT_CASES[name]).read_text()
    assert len(COPY_CALL.findall(text)) == EXPECTED_COPIES[name]


SMALL = """\
struct Small
    x: i64
    y: i64

pub fn mk(a: i64) -> Small
    return Small { x: a, y: 2 }
"""


@pytest.mark.integration
def test_small_struct_lit_stays_first_class(tmp_path):
    """Below 256 bytes a literal stays an SROA-friendly insertvalue chain."""
    text = _ritz0_ll(tmp_path, "small", SMALL).read_text()
    assert re.search(r'insertvalue %"?[\w.]*Small"?', text), text[-2000:]


# --- behaviour --------------------------------------------------------------
#
# 4 rows = 692 bytes: over the threshold, small enough that the old
# first-class IR compiled too.  Field initialisers run in source order and
# may read the destination's old value (`b = Big { count: b.count + 1, ... }`).

RUN = DECLS.format(n=4).replace(
    "extern fn sink(p: *Big) -> i32\n"
    "extern fn sink_v(b: Big) -> i32\n"
    "extern fn sink_o(p: *Outer) -> i32\n",
    "",
) + f"""
var g_trace: i32 = 0

fn step(d: i32) -> i32
    g_trace = g_trace * 10 + d
    return d

fn total(p: *Big) -> i32
    return p.count + p.rows[3].name[7] as i32 + p.rows[0].b + p.rows[2].id

fn take(b: Big) -> i32
    return total(@b)

fn mk(c: i32) -> Big
    return Big {{ rows: [{ROW_SET}; 4], count: c }}

fn mk_order() -> Big
    return Big {{ count: step(2), rows: [Row {{ id: step(1), name: [0; 32], pat: [0; 128], a: 0, b: 0 }}; 4] }}

pub fn main() -> i32
    # return of a literal (sret), non-zero fill
    var a: Big = mk(5)
    if total(@a) != 5 + 7 + 3 + 1
        return 1
    # var init from a literal
    var b: Big = Big {{ rows: [{ROW}; 4], count: 6 }}
    if total(@b) != 6
        return 2
    @ZEROED@
    # assignment whose initialisers read the old value of the destination
    # (scalars only: ritz1 cannot lower `rows: b.rows` yet, AGAST #1748)
    b.rows[0].b = 40
    b = Big {{ rows: [Row {{ id: b.count, name: [0; 32], pat: [0; 128], a: 0, b: b.rows[0].b + 1 }}; 4], count: b.count + 1 }}
    if b.count != 7 or b.rows[0].b != 41 or b.rows[3].id != 6
        return 4
    # by-value argument
    if take(Big {{ rows: [{ROW_SET}; 4], count: 2 }}) != 2 + 7 + 3 + 1
        return 5
    # nested large literal
    var o: Outer = Outer {{ tag: 8, big: Big {{ rows: [{ROW_SET}; 4], count: 1 }} }}
    if o.tag != 8 or total(@o.big) != 1 + 7 + 3 + 1
        return 6
    # nested field from an existing value
    let pa: *Big = @a
    var o2: Outer = Outer {{ tag: 9, big: *pa }}
    a.count = 0
    if o2.tag != 9 or total(@o2.big) != 5 + 7 + 3 + 1
        return 7
    # nested field from an sret call
    var o3: Outer = Outer {{ tag: 4, big: mk(2) }}
    if o3.tag != 4 or total(@o3.big) != 2 + 7 + 3 + 1
        return 9
    # field initialisers run in source order
    g_trace = 0
    var m: Big = mk_order()
    if g_trace != 21 or m.count != 2 or m.rows[3].id != 1
        return 8
    return 42
"""


# Omitted fields are zeroed (ritz0 only, see the test docstring).  Dirty the
# stack first so a missing memset cannot pass by luck.
ZEROED = """\
    var junk: Big = mk(9)
    junk.rows[1].pat[100] = 5
    var z: Big = Big { count: 3 }
    if total(@z) != 3 or z.rows[1].pat[100] != 0 or z.rows[3].name[7] != 0
        return 3
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ("ritz0", "ritz1"))
def test_large_struct_lits_run_at_O2(ritz1_bin, tmp_path, compiler):  # noqa: F811
    """ritz1 runs the same program as an oracle, minus the omitted-field case:
    ritz1 leaves omitted fields uninitialised (AGAST #1749)."""
    if compiler == "ritz0":
        ll = _ritz0_ll(tmp_path, "run", RUN.replace("    @ZEROED@\n", ZEROED))
        text = ll.read_text()
        bad = [ln.strip() for ln in text.splitlines() if FIRST_CLASS.search(ln)]
        assert not bad, f"first-class large-struct values survive: {bad[:5]}"
    else:
        ll = _ritz1_ll(tmp_path, "run", RUN.replace("    @ZEROED@\n", ""))
    obj = _o2_object(ll)
    _assert_no_libc_mem(obj)
    exe = tmp_path / f"run_{compiler}"
    assert _link_run([obj], exe, with_start=(compiler == "ritz1")) == 42
