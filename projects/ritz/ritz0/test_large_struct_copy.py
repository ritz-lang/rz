"""AGAST #1732: large struct COPIES never form a first-class LLVM value.

THE DEFECT

#1730 (ritz1) and #1736 (ritz0) moved large struct RETURNS to sret.  Every
other copy of a large struct still went through a first-class aggregate:

    %v = load %Big, ptr %src
    store %Big %v, ptr %dst

That is `var x: Big = *p`, `let y = *p`, `x = y`, `x = f()`, `*q = *p`,
`o.big = *p`, and in ritz1 also `var x: Big = f()` (the sret slot was loaded
and re-stored).  At -O2 InstCombine splits such a load/store into one scalar
per leaf; for the 22 KB shape of tokens.ritz's %TokenDefs (~21k leaves) clang
grows without bound.

THE FIX

Both compilers rewrite `store %T %v, ptr %dst`, for a struct %T of at least
256 bytes (the sret threshold), when %v is `load %T, ptr %src` and no
instruction between the load and the store can write memory, into

    call void @__ritz_sret_copy(ptr %dst, ptr %src, i64 sizeof(%T))

The load is left dead and is deleted before InstCombine sees it.  Because
nothing can write memory between the load and the store, copying from %src
at the store gives the same bytes the load would have.  The helper is a
"no-builtins" byte loop: Ritz links -nostdlib, and llvm.memcpy at this size
lowers to a libc call.

BY-VALUE PARAMS are not covered here: passing a large struct by value is an
ABI change for both compilers, tracked as AGAST #1739.

Every clang -O2 run is bounded (see test_ritz1_large_struct_ret._clang_bounded).
"""

import os
import re
import subprocess

import pytest

from test_ritz1_large_struct_ret import (
    _assert_no_libc_mem,
    _link_run,
    _o2_object,
    _ritz0_ll,
    _ritz1_ll,
)
from test_ritz1_builtin_struct_shadow import RITZ_ROOT

SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"

COMPILERS = ("ritz0", "ritz1")

# ritz1: `call void @__ritz_sret_copy(`; llvmlite quotes: `@"__ritz_sret_copy"(`
COPY_CALL = re.compile(r'call void @"?__ritz_sret_copy"?\(')


def _ll(compiler: str, tmp_path, name: str, program: str):
    if compiler == "ritz0":
        return _ritz0_ll(tmp_path, name, program)
    if compiler == "ritz1":
        return _ritz1_ll(tmp_path, name, program)
    # ritz1_selfhosted: the gate builds it before pytest.
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    comp = subprocess.run(
        [str(SELFHOSTED_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return ll


# --- the 22 KB shape, with no large-struct constructor in the module --------
#
# big_new / sink are extern so the only large first-class values are the
# copies under test (ritz0 still builds a huge struct LITERAL first-class,
# AGAST #1741).

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

extern fn big_new() -> Big
extern fn sink(p: *Big) -> i32
"""

HUGE = DECLS.format(n=128)

COPY_CASES = {
    "var_init_call": """
pub fn use1() -> i32
    var x: Big = big_new()
    return sink(@x)
""",
    "let_init_call": """
pub fn use1() -> i32
    let x = big_new()
    return x.count
""",
    "assign_call": """
pub fn use1(p: *Big) -> i32
    var x: Big = *p
    x = big_new()
    return sink(@x)
""",
    "assign_var": """
pub fn use1() -> i32
    var x: Big = big_new()
    var y: Big = big_new()
    y.count = 3
    x = y
    return sink(@x)
""",
    "var_deref": """
pub fn use1(p: *Big) -> i32
    var y: Big = *p
    return sink(@y)
""",
    "let_deref": """
pub fn use1(p: *Big) -> i32
    let y = *p
    return y.count
""",
    "store_deref": """
pub fn use1(p: *Big, q: *Big) -> i32
    *q = *p
    return 0
""",
    "field_assign": """
pub fn use1(p: *Big, o: *Outer) -> i32
    o.big = *p
    return o.tag
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(COPY_CASES))
def test_huge_struct_copy_compiles_at_O2_within_bound(
    ritz1_bin,
    tmp_path,
    compiler,
    name,
):
    ll = _ll(compiler, tmp_path, name, HUGE + COPY_CASES[name])
    _assert_no_libc_mem(_o2_object(ll))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(COPY_CASES))
def test_large_struct_copy_has_no_first_class_store(
    ritz1_bin,
    tmp_path,
    compiler,
    name,
):
    """The IR shape: no `store %Big` survives, a copy call replaces it.

    A first-class copy still compiles quickly at small sizes and still runs,
    so only the IR shows a path that missed the rewrite.
    """
    text = _ll(compiler, tmp_path, name, HUGE + COPY_CASES[name]).read_text()
    # `store %Big %v` (ritz1) / `store %"struct.m.Big" %v` (ritz0); a
    # `store %Big* ...` pointer store is fine.
    stores = [
        ln.strip()
        for ln in text.splitlines()
        if re.match(r'\s*store %"?[\w.]*Big"? %', ln)
    ]
    assert not stores, f"first-class large-struct stores survive: {stores}"
    # No copy at all: ritz0 writes a var-init sret call into the var's slot
    # (#1736) and binds an immutable `let` to the loaded SSA value (only
    # its fields are ever extracted, which -O2 narrows to scalar loads).
    no_copy = {
        ("ritz0", "var_init_call"),
        ("ritz0", "let_init_call"),
        ("ritz0", "let_deref"),
    }
    if (compiler, name) not in no_copy:
        assert COPY_CALL.search(text), "no copy helper call was emitted"


# --- AGAST #1748: a struct literal's array field from a non-literal ---------
#
# `Big { rows: p.rows, .. }` copies the `[N x %Row]` into the literal's slot.
# A large one goes pointer-to-pointer like any other large copy; a first-class
# `[N x %Row]` load/store is what clang -O2 explodes per element.

ARRAY_FIELD_LIT = HUGE + """
pub fn use1(p: *Big) -> i32
    var x: Big = Big { rows: p.rows, count: 1 }
    return sink(@x)
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_array_field_literal_copies_pointer_to_pointer(ritz1_bin, tmp_path, compiler):
    text = _ll(compiler, tmp_path, "array_field_lit", ARRAY_FIELD_LIT).read_text()
    first_class = [
        ln.strip()
        for ln in text.splitlines()
        if re.search(r'(load|store) \[128 x %"?[\w.]*Row"?\]', ln)
    ]
    assert not first_class, f"first-class large-array copies survive: {first_class}"
    assert COPY_CALL.search(text), "no copy helper call was emitted"
    _assert_no_libc_mem(_o2_object(_ll(compiler, tmp_path, "array_field_lit", ARRAY_FIELD_LIT)))


# --- behaviour, with a size small enough for ritz0's old IR as well ---------

# 4 rows = 692 bytes: over the 256-byte threshold, so the rewrite engages.
MID = DECLS.format(n=4).replace(
    "extern fn big_new() -> Big\nextern fn sink(p: *Big) -> i32\n",
    """\
fn big_make(n: i32) -> Big
    var b: Big = Big {
        rows: [Row { id: 0, name: [0; 32], pat: [0; 128], a: 0, b: 0 }; 4],
        count: n
    }
    b.rows[3].name[7] = (n + 1) as u8
    b.rows[0].b = n * 2
    return b

fn total(p: *Big) -> i32
    return p.count + p.rows[3].name[7] as i32 + p.rows[0].b
""",
)

RUN = (
    MID
    + """
pub fn main() -> i32
    var src: Big = big_make(5)
    # var init from deref, then mutate the source: the copy is a snapshot.
    let p: *Big = @src
    var a: Big = *p
    src.count = 100
    if total(@a) != 5 + 6 + 10
        return 1
    # let from deref
    let b: Big = *p
    src.count = 7
    if b.count != 100
        return 2
    # assignment from a var (which it moves), then mutate the destination
    var c: Big = big_make(1)
    let pa: *Big = @a
    var a2: Big = *pa
    c = a2
    c.rows[0].b = 0
    if total(@c) != 5 + 6
        return 3
    if total(@a) != 5 + 6 + 10
        return 4
    # assignment from a call result
    c = big_make(9)
    if total(@c) != 9 + 10 + 18
        return 5
    # store through a pointer
    var d: Big = big_make(0)
    let q: *Big = @d
    *q = *p
    if d.count != 7
        return 6
    # store into a field
    var o: Outer = Outer { tag: 3, big: big_make(2) }
    o.big = *pa
    if total(@o.big) != 5 + 6 + 10 or o.tag != 3
        return 7
    # self-assignment through a pointer is harmless
    let pc: *Big = @c
    *pc = *pc
    if total(@c) != 9 + 10 + 18
        return 8
    return 42
"""
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_struct_copies_run_at_O2(ritz1_bin, tmp_path, compiler):
    ll = _ll(compiler, tmp_path, "run", RUN)
    assert COPY_CALL.search(ll.read_text()), "the copy rewrite did not engage"
    obj = _o2_object(ll)
    _assert_no_libc_mem(obj)
    exe = tmp_path / f"run_{compiler}"
    assert _link_run([obj], exe, with_start=(compiler == "ritz1")) == 42


SMALL = """\
struct Small
    x: i64
    y: i64

pub fn use1(p: *Small) -> i64
    var s: Small = *p
    return s.x + s.y
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_small_struct_copy_is_unchanged(ritz1_bin, tmp_path, compiler):
    """Below 256 bytes a copy stays a first-class load/store (SROA-friendly)."""
    text = _ll(compiler, tmp_path, "small", SMALL).read_text()
    assert "__ritz_sret_copy" not in text


# --- the rewrite never reads the source after a write -----------------------
#
# Each program writes the copy's source from a call evaluated as part of the
# store's DESTINATION.  §13.6 (LARB R61) runs that call before the source is
# read, so every program exits 77 (AGAST #1740: ritz0 read the source first
# for `*f() = *p` and `f().big = *p`, and ritz1 for `*f() = *p`).  The rewrite
# must not change it: the same program with 1 row (184 bytes, below the
# threshold, so no rewrite) must exit with the same code as with 4 rows
# (692 bytes).

ORDER_DECLS = """\
struct Row
    id: i32
    name: [32]u8
    pat: [128]u8
    a: i32
    b: i32

struct Big
    rows: [{n}]Row
    count: i32

fn bump_idx(p: *Big) -> i64
    p.count = 77
    return 1

fn bump_ptr(p: *Big, d: *Big) -> *Big
    p.count = 77
    return d

struct Outer
    tag: i32
    big: Big

fn bump_o(p: *Big, o: *Outer) -> *Outer
    p.count = 77
    return o

fn fresh(c: i32) -> Big
    return Big {{ rows: [Row {{ id: 0, name: [0; 32], pat: [0; 128], a: 0, b: 0 }}; {n}], count: c }}
"""

ORDER_CASES = {
    # bump_idx in the index, then load *p, then store.
    "index_call": """
pub fn main() -> i32
    var src: Big = fresh(5)
    let p: *Big = @src
    var arr: [2]Big
    arr[bump_idx(p)] = *p
    return arr[1].count
""",
    # call bump_ptr; load *p; store.
    "deref_call_lvalue": """
pub fn main() -> i32
    var src: Big = fresh(5)
    let p: *Big = @src
    var d: Big = fresh(1)
    *bump_ptr(p, @d) = *p
    return d.count
""",
    # call bump_o; load *p; store into its `.big` (ritz0 read *p first: 5).
    "member_call_lvalue": """
pub fn main() -> i32
    var src: Big = fresh(5)
    let p: *Big = @src
    var o: Outer = Outer { tag: 0, big: fresh(1) }
    bump_o(p, @o).big = *p
    return o.big.count
""",
}

ORDER_PARAMS = [
    (compiler, name)
    for name in ORDER_CASES
    for compiler in ("ritz0", "ritz1", "ritz1_selfhosted")
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", ORDER_PARAMS)
def test_large_copy_keeps_evaluation_order(ritz1_bin, tmp_path, compiler, name):
    codes = {}
    for n in (1, 4):
        ll = _ll(
            compiler,
            tmp_path,
            f"{name}_{n}",
            ORDER_DECLS.format(n=n) + ORDER_CASES[name],
        )
        exe = tmp_path / f"{name}_{n}_{compiler}"
        codes[n] = _link_run([_o2_object(ll)], exe, with_start=(compiler != "ritz0"))
    assert codes[1] == 77, f"{name} read the source before the place's call: {codes}"
    assert codes[4] == codes[1], (
        f"the large copy changed the result: {codes[4]} with the rewrite, "
        f"{codes[1]} without"
    )


# --- ritz1's scanner, driven with hand-written IR ----------------------------
#
# Both compilers evaluate an assignment's destination before its source
# (§13.6), so no Ritz program puts a write between the load and the store, and the
# evaluation-order test above cannot reach ritz1's "nothing writes memory in
# between" check.  These cases call ritz1/src/ll_copy_scan.ritz directly.
# (expected, IR body whose LAST line is the store under test)

SCAN_CASES = {
    "adjacent": (1, "  %.5 = load %Big, ptr %.4\n  store %Big %.5, ptr %.2\n"),
    "pure_between": (
        1,
        "  %.5 = load %Big, ptr %.4\n"
        "  %.6 = getelementptr %Big, ptr %.2, i32 0, i32 1\n"
        "  %.7 = ptrtoint ptr %.6 to i64\n"
        "  %.8 = load i64, ptr %.1\n"
        "  store %Big %.5, ptr %.2\n",
    ),
    "call_value_between": (
        0,
        "  %.5 = load %Big, ptr %.4\n  %.6 = call i64 @bump(i64 1)\n  store %Big %.5, ptr %.2\n",
    ),
    "call_void_between": (
        0,
        "  %.5 = load %Big, ptr %.4\n  call void @bump()\n  store %Big %.5, ptr %.2\n",
    ),
    "store_between": (
        0,
        "  %.5 = load %Big, ptr %.4\n  store i32 7, ptr %.4\n  store %Big %.5, ptr %.2\n",
    ),
    "label_between": (
        0,
        "  %.5 = load %Big, ptr %.4\n  br label %L1\nL1:\n  store %Big %.5, ptr %.2\n",
    ),
    "atomicrmw_between": (
        0,
        "  %.5 = load %Big, ptr %.4\n"
        "  %.6 = atomicrmw add ptr %.9, i64 1 seq_cst\n"
        "  store %Big %.5, ptr %.2\n",
    ),
    "not_a_load": (0, "  %.5 = phi %Big [ %.3, %L1 ]\n  store %Big %.5, ptr %.2\n"),
    "other_type_load": (0, "  %.5 = load %BigX, ptr %.4\n  store %Big %.5, ptr %.2\n"),
    "constant_value": (0, "  store %Big zeroinitializer, ptr %.2\n"),
    "reg_prefix_is_not_def": (
        0,
        "  %.55 = load %Big, ptr %.4\n  store %Big %.5, ptr %.2\n",
    ),
}


def _ritz_cstr(s: str) -> str:
    return 'c"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _scan_program() -> str:
    lines = [
        "import ritzlib.sys",
        "import ll_copy_scan",
        "",
        "fn cstrlen(p: *u8) -> i64",
        "    var n: i64 = 0",
        "    while *(p + n) != 0",
        "        n += 1",
        "    n",
        "",
        "# 1 when the copy found in `text` matches the expectation.",
        "fn check(text: *u8, expect: i32) -> i32",
        "    let n: i64 = cstrlen(text)",
        "    var li: i64 = n - 1",
        "    while li > 0 and *(text + li - 1) != 10",
        "        li -= 1",
        "    let last: *u8 = text + li",
        "    var cp: LlCopy",
        "    let got: i32 = ll_find_copy(text, last, n - li, @cp)",
        "    if got != expect",
        "        return 0",
        "    if got == 1",
        "        # src is %.4 and dst is %.2 in every positive case",
        "        if cp.src_len != 3 or *(cp.src + 2) != 52",
        "            return 0",
        "        if cp.dst_len != 3 or *(last + cp.dst_off + 2) != 50",
        "            return 0",
        "    1",
        "",
        "pub fn main() -> i32",
    ]
    for i, name in enumerate(sorted(SCAN_CASES), start=1):
        expect, text = SCAN_CASES[name]
        lines.append(f"    if check({_ritz_cstr(text)}, {expect}) == 0")
        lines.append(f"        return {i}")
    lines.append("    return 0")
    return "\n".join(lines) + "\n"


@pytest.mark.integration
def test_ritz1_copy_scanner_stops_at_writes(tmp_path):
    import os
    import subprocess

    from test_ritz1_large_struct_ret import RITZ0, RITZ_ROOT

    src = tmp_path / "scan.ritz"
    src.write_text(_scan_program())
    ll = tmp_path / "scan.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{RITZ_ROOT / 'ritz1' / 'src'}")
    comp = subprocess.run(
        ["python3", str(RITZ0), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0, comp.stdout[-2000:] + comp.stderr[-2000:]
    # Imports are only declared; compile the module itself as ritz1's
    # Makefile does.
    mod_ll = tmp_path / "ll_copy_scan.ll"
    mod = subprocess.run(
        [
            "python3",
            str(RITZ0),
            str(RITZ_ROOT / "ritz1" / "src" / "ll_copy_scan.ritz"),
            "--no-runtime",
            "-o",
            str(mod_ll),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert mod.returncode == 0, mod.stdout[-2000:] + mod.stderr[-2000:]
    rc = _link_run(
        [_o2_object(ll), _o2_object(mod_ll)], tmp_path / "scan", with_start=False
    )
    names = sorted(SCAN_CASES)
    assert rc == 0, (
        f"scanner case failed: {names[rc - 1] if 0 < rc <= len(names) else rc}"
    )


# --- AGAST #3696: an if / match that yields a large struct -------------------
#
# Both compilers merged the arms through `phi %Big` and stored the phi:
#
#     %.14 = phi %Big [ %.10, %L0 ], [ %.13, %L1 ]
#     store %Big %.14, ptr %r.addr
#
# A phi is not a load, so the copy rewrite above never fired, and the
# first-class %Big is what sends clang -O2 superlinear.  Now each arm copies
# into a result slot (or an sret call writes it directly) and the merge reads
# the slot, so no `phi %Big` and no `store %Big %` remain.

MERGE_FNS = """
enum Pick
    A
    B
    C

pub fn if_let(b: bool, p: *Big, q: *Big) -> i32
    let r: Big = if b then *p else *q
    return sink(@r)

pub fn match_var(t: Pick, p: *Big, q: *Big) -> i32
    var c: Big = match t
        A => *p
        B => *q
        C => big_new()
    return sink(@c)

pub fn if_call(b: bool, p: *Big) -> i32
    var r: Big = if b then big_new() else *p
    return sink(@r)

pub fn nested(a: bool, b: bool, p: *Big, q: *Big) -> i32
    var r: Big = if a then *p else if b then *q else big_new()
    return sink(@r)

pub fn assign(b: bool, p: *Big, q: *Big) -> i32
    var r: Big = *p
    r = if b then *q else *p
    return sink(@r)

pub fn store_deref(b: bool, p: *Big, q: *Big, d: *Big) -> i32
    *d = if b then *p else *q
    return 0

pub fn ret(b: bool, p: *Big, q: *Big) -> Big
    return if b then *p else *q
"""

MERGE_HUGE = HUGE + MERGE_FNS

# `phi %Big` (ritz1) / `phi  %"struct.m.Big"` (ritz0), and `store %Big %v`.
FIRST_CLASS_MERGE = re.compile(r'(=\s*phi\s+%"?[\w.]*Big"?\s|^\s*store %"?[\w.]*Big"? %)')


def _first_class_merges(ll) -> list:
    return [ln.strip() for ln in ll.read_text().splitlines() if FIRST_CLASS_MERGE.search(ln)]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_struct_if_match_merges_through_a_slot(ritz1_bin, tmp_path, compiler):
    """No `phi %Big` / `store %Big %`, and clang -O2 on the 22 KB Big is bounded."""
    ll = _ll(compiler, tmp_path, "merge", MERGE_HUGE)
    bad = _first_class_merges(ll)
    assert not bad, f"first-class large-struct merges survive: {bad}"
    assert COPY_CALL.search(ll.read_text()), "no copy helper call was emitted"
    _assert_no_libc_mem(_o2_object(ll))


MERGE_RUN_DECLS = """\
enum Pick
    A
    B
    C

var CLOBBER: *Big = null

struct Guard
    id: i32

impl Drop for Guard
    fn drop(self: @&Guard)
        CLOBBER.count = 9

"""

MERGE_RUN = (
    MID.replace("struct Outer", MERGE_RUN_DECLS + "struct Outer")
    + """
fn pick_if(b: bool, p: *Big, q: *Big) -> i32
    let r: Big = if b then *p else *q
    return total(@r)

fn pick_match(t: Pick, p: *Big, q: *Big) -> i32
    var c: Big = match t
        A => *p
        B => *q
        C => big_make(30)
    return total(@c)

fn pick_nested(a: bool, b: bool, p: *Big, q: *Big) -> i32
    var r: Big = if a then *p else if b then big_make(40) else *q
    return total(@r)

fn pick_ret(b: bool, p: *Big, q: *Big) -> Big
    return if b then *p else *q

# The arm's value is `*p` as loaded, before `g`'s drop writes p.count: the
# drop runs between the load and the arm's branch to the merge.
fn pick_drop(b: bool, p: *Big, q: *Big) -> i32
    CLOBBER = p
    let r: Big = if b
        var g: Guard = Guard { id: 1 }
        *p
    else
        *q
    return total(@r)

pub fn main() -> i32
    var x: Big = big_make(1)
    var y: Big = big_make(2)
    let tx: i32 = total(@x)
    let ty: i32 = total(@y)
    if pick_if(true, @x, @y) != tx
        return 1
    if pick_if(false, @x, @y) != ty
        return 2
    if pick_match(Pick.A, @x, @y) != tx
        return 3
    if pick_match(Pick.B, @x, @y) != ty
        return 4
    if pick_match(Pick.C, @x, @y) != 30 + 31 + 60
        return 5
    if pick_nested(true, false, @x, @y) != tx
        return 6
    if pick_nested(false, true, @x, @y) != 40 + 41 + 80
        return 7
    if pick_nested(false, false, @x, @y) != ty
        return 8
    var r: Big = pick_ret(false, @x, @y)
    if total(@r) != ty
        return 9
    # The slot is reused on every pass: each merged value is its own copy.
    var i: i32 = 0
    var sum: i32 = 0
    while i < 4
        var z: Big = if i % 2 == 0 then x else y
        z.count = z.count + i
        sum = sum + total(@z)
        i = i + 1
    if sum != 2 * tx + 2 * ty + 0 + 1 + 2 + 3
        return 10
    if x.count != 1 or y.count != 2
        return 11
    var w: Big = big_make(1)
    if pick_drop(true, @w, @y) != tx
        return 12
    if w.count != 9
        return 13
    return 42
"""
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_struct_if_match_picks_the_right_arm_at_O2(ritz1_bin, tmp_path, compiler):
    ll = _ll(compiler, tmp_path, "merge_run", MERGE_RUN)
    bad = _first_class_merges(ll)
    assert not bad, f"the merge did not go through a slot: {bad}"
    obj = _o2_object(ll)
    _assert_no_libc_mem(obj)
    exe = tmp_path / f"merge_run_{compiler}"
    assert _link_run([obj], exe, with_start=(compiler == "ritz1")) == 42
