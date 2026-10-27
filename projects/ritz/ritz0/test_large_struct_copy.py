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

import re

import pytest

from test_ritz1_large_struct_ret import (
    _assert_no_libc_mem,
    _link_run,
    _o2_object,
    _ritz0_ll,
    _ritz1_ll,
)

COMPILERS = ("ritz0", "ritz1")

# ritz1: `call void @__ritz_sret_copy(`; llvmlite quotes: `@"__ritz_sret_copy"(`
COPY_CALL = re.compile(r'call void @"?__ritz_sret_copy"?\(')


def _ll(compiler: str, tmp_path, name: str, program: str):
    if compiler == "ritz0":
        return _ritz0_ll(tmp_path, name, program)
    return _ritz1_ll(tmp_path, name, program)


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
    # Annotated: ritz1 cannot yet infer `let y = *p` for a struct pointer
    # (a separate inference gap, AGAST #1740).
    "let_deref": """
pub fn use1(p: *Big) -> i32
    let y: Big = *p
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
# store's DESTINATION.  Whether that call runs before or after the source is
# read is the compiler's evaluation order; the rewrite must not change it.
# Oracle: the same program with 1 row (184 bytes, below the threshold, so no
# rewrite) must exit with the same code as with 4 rows (692 bytes).

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

fn fresh(c: i32) -> Big
    return Big {{ rows: [Row {{ id: 0, name: [0; 32], pat: [0; 128], a: 0, b: 0 }}; {n}], count: c }}
"""

ORDER_CASES = {
    # load *p, then bump_idx in the index, then store (ritz0 order), or the
    # call first (ritz1 order).
    "index_call": """
pub fn main() -> i32
    var src: Big = fresh(5)
    let p: *Big = @src
    var arr: [2]Big
    arr[bump_idx(p)] = *p
    return arr[1].count
""",
    # ritz0 emits load *p; call bump_ptr; store — the guard case.  ritz1
    # cannot compile a deref-of-call lvalue of struct type yet (#1740: it stores
    # `i64`), so this one is ritz0 only.
    "deref_call_lvalue": """
pub fn main() -> i32
    var src: Big = fresh(5)
    let p: *Big = @src
    var d: Big = fresh(1)
    *bump_ptr(p, @d) = *p
    return d.count
""",
}

ORDER_PARAMS = [
    ("ritz0", "index_call"),
    ("ritz1", "index_call"),
    ("ritz0", "deref_call_lvalue"),
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
        codes[n] = _link_run([_o2_object(ll)], exe, with_start=(compiler == "ritz1"))
    assert codes[1] in (5, 77), codes
    assert codes[4] == codes[1], (
        f"the large copy changed the result: {codes[4]} with the rewrite, "
        f"{codes[1]} without"
    )


# --- ritz1's scanner, driven with hand-written IR ----------------------------
#
# ritz1 evaluates an assignment's destination before its source today, so no
# Ritz program puts a write between the load and the store, and the
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
