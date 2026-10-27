"""AGAST #1739: large by-value struct params are `ptr byval(%T) align N`.

THE DEFECT

#1730/#1736 moved large struct RETURNS to sret and #1732 moved large struct
COPIES to `@__ritz_sret_copy`.  A by-value PARAMETER of a large struct was
still a first-class aggregate in both compilers:

    define i32 @take(%Big %b.arg) {
      %b = alloca %Big
      store %Big %b.arg, ptr %b

and every caller loaded the argument into a first-class `%Big` register.  For
the 22 KB shape of tokens.ritz's %TokenDefs, clang -O2 grows without bound
on that store.  The first-class form was also not the C ABI: LLVM splits a
first-class aggregate argument into one scalar per leaf, while C passes it in
memory.

THE FIX (an ABI change both compilers make together)

A param whose type is a named struct of at least 256 bytes (the sret
threshold) is passed as `ptr byval(%T) align max(8, alignof T)`: exactly what
clang emits for a C `struct T` param on x86-64 SysV.  The callee binds the
param to the byval pointer (the caller's copy, which the callee owns); the
caller spills the argument into a fresh slot (pointer-to-pointer via
@__ritz_sret_copy when it is a load, #1732) and passes that slot.  Smaller
structs keep their ABI.

The interop tests link ritz0 against ritz1 and both against clang-compiled C,
in both directions.  Every clang -O2 run is bounded.
"""

import re
from pathlib import Path

import pytest

from test_ritz1_large_struct_ret import (
    _assert_no_libc_mem,
    _clang_bounded,
    _link_run,
    _o2_object,
    _ritz0_ll,
    _ritz1_ll,
)

COMPILERS = ("ritz0", "ritz1")


def _ll(compiler: str, tmp_path: Path, name: str, program: str) -> Path:
    if compiler == "ritz0":
        return _ritz0_ll(tmp_path, name, program)
    return _ritz1_ll(tmp_path, name, program)


# ritz1 writes `%Big`; ritz0 (llvmlite) writes `%"struct.ritz_module_1.Big"`.
BIG_T = r'%"?(?:struct\.[\w.]*\.)?Big"?'
SMALL_T = r'%"?(?:struct\.[\w.]*\.)?Small"?'
BYVAL_BIG = rf"byval\({BIG_T}\) align 8"


def _header(text: str, kind: str, fn: str) -> str:
    """The `define`/`declare` line of @fn (llvmlite quotes the name)."""
    pat = re.compile(rf'^{kind}\b.*@"?{re.escape(fn)}"?\(')
    for line in text.splitlines():
        if pat.search(line):
            return line
    raise AssertionError(f"no {kind} for @{fn}:\n{text[-3000:]}")


def _calls(text: str, fn: str) -> list:
    pat = re.compile(rf'call [^@]*@"?{re.escape(fn)}"?\(')
    return [line for line in text.splitlines() if pat.search(line)]


# --- the 22 KB shape of tokens.ritz -----------------------------------------
#
# big_new / sink are extern, so the only large first-class values are the
# params under test (ritz0 still builds a huge struct LITERAL first-class,
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

extern fn big_new() -> Big
extern fn sink(p: *Big) -> i32
"""

HUGE = DECLS.format(n=128)

PARAM_CASES = {
    # The ticket repro: a param copied into a local.
    "param_copy": """
pub fn take(b: Big) -> i32
    var c: Big = b
    return sink(@c)
""",
    "param_fields": """
pub fn take(b: Big) -> i32
    return b.count + b.rows[3].a
""",
    "param_address": """
pub fn take(b: Big) -> i32
    return sink(@b)
""",
    "param_mutated": """
pub fn take(b: Big) -> i32
    var c: Big = b
    c.count = 3
    return sink(@c)
""",
    "method_param": """
impl Big
    fn absorb(self: @&Big, other: Big) -> i32
        return self.count + other.count
""",
    "call_with_local": """
pub fn take(b: Big) -> i32
    return b.count

pub fn caller() -> i32
    var x: Big = big_new()
    return take(x)
""",
    "call_with_deref": """
pub fn take(b: Big) -> i32
    return b.count

pub fn caller(p: *Big) -> i32
    return take(*p)
""",
    "call_with_sret_result": """
pub fn take(b: Big) -> i32
    return b.count

pub fn caller() -> i32
    return take(big_new())
""",
    "call_extern": """
extern fn ext_take(b: Big) -> i32

pub fn caller(p: *Big) -> i32
    return ext_take(*p)
""",
    "call_method": """
impl Big
    fn absorb(self: @&Big, other: Big) -> i32
        return self.count + other.count

pub fn caller(p: *Big, q: *Big) -> i32
    return p.absorb(*q)
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PARAM_CASES))
def test_huge_struct_param_compiles_at_O2_within_bound(
    ritz1_bin,
    tmp_path,
    compiler,
    name,
):
    ll = _ll(compiler, tmp_path, name, HUGE + PARAM_CASES[name])
    _assert_no_libc_mem(_o2_object(ll))


# --- IR shape ---------------------------------------------------------------

SHAPE = (
    DECLS.format(n=4)
    + """
struct Small
    x: i64
    y: i64

extern fn ext_take(b: Big) -> i32

pub fn take(b: Big) -> i32
    return b.count

pub fn small_take(s: Small) -> i64
    return s.x + s.y

impl Big
    fn absorb(self: @&Big, other: Big) -> i32
        return self.count + other.count

    fn from_other(other: Big) -> i32
        return other.count

pub fn caller(p: *Big, q: *Big) -> i32
    var s: Small = Small { x: 1, y: 2 }
    let a = take(*p)
    let b = p.absorb(*q)
    let c = ext_take(*q)
    let d = Big.from_other(*p)
    return a + b + c + d + small_take(s) as i32
"""
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_param_definitions_are_byval(ritz1_bin, tmp_path, compiler):
    text = _ll(compiler, tmp_path, "shape", SHAPE).read_text()
    for fn in ("take", "Big_absorb", "Big_from_other"):
        hdr = _header(text, "define", fn)
        assert re.search(BYVAL_BIG, hdr), f"@{fn} does not take ptr byval(%Big):\n{hdr}"
        assert not re.search(rf"[(,] *{BIG_T} %", hdr), (
            f"@{fn} still takes %Big first-class:\n{hdr}"
        )
    # No first-class store of a param into its slot.
    assert not re.search(rf"store {BIG_T} %\"?\w+\.arg", text), (
        "a large param is still spilled first-class"
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_param_extern_declare_is_byval(ritz1_bin, tmp_path, compiler):
    text = _ll(compiler, tmp_path, "shape", SHAPE).read_text()
    hdr = _header(text, "declare", "ext_take")
    assert re.search(BYVAL_BIG, hdr), hdr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_param_every_call_path_passes_byval(ritz1_bin, tmp_path, compiler):
    """Direct, method, extern and static-method calls all pass a byval slot."""
    text = _ll(compiler, tmp_path, "shape", SHAPE).read_text()
    for fn in ("take", "Big_absorb", "ext_take", "Big_from_other"):
        calls = _calls(text, fn)
        assert calls, f"no call to @{fn}"
        for line in calls:
            assert re.search(BYVAL_BIG, line), f"call to @{fn} is not byval:\n{line}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_small_struct_param_is_unchanged(ritz1_bin, tmp_path, compiler):
    """A 16-byte struct is still passed first-class: no ABI change below 256 B."""
    text = _ll(compiler, tmp_path, "shape", SHAPE).read_text()
    hdr = _header(text, "define", "small_take")
    assert "byval" not in hdr and re.search(rf"\({SMALL_T} %", hdr), hdr


# --- behaviour --------------------------------------------------------------

# 4 rows = 692 bytes: over the threshold, small enough to run quickly.
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
# The callee owns its copy: writing it must not reach the caller.
fn scribble(b: Big) -> i32
    var c: Big = b
    c.count = 1000
    let before = total(@b)
    return before + c.count - 1000

fn take2(b: Big, n: i32) -> i32
    return total(@b) * 100 + n

fn bump(p: *Big) -> i32
    p.count = p.count + 50
    return 7

fn pass_on(b: Big) -> i32
    return scribble(b)

impl Big
    fn plus(self: @&Big, other: Big) -> i32
        return self.count + total(@other)

    # i64, not i32: ritz1 uses a static method's i32 result as i64 (#1733).
    fn of(other: Big) -> i64
        return total(@other) as i64

pub fn main() -> i32
    var x: Big = big_make(5)
    # By-value passing moves a local, so args that are reused go as `*p`.
    let p: *Big = @x
    # deref arg; the callee writes its copy, which must not reach x
    if scribble(*p) != 5 + 6 + 10
        return 1
    if x.count != 5
        return 2
    # sret result as the arg
    if scribble(big_make(2)) != 2 + 3 + 4
        return 3
    # a param passed on again
    if pass_on(*p) != 21
        return 4
    # method and static method
    var y: Big = big_make(1)
    if x.plus(y) != 5 + 1 + 2 + 2
        return 5
    if Big.of(*p) != 21
        return 6
    # The arg is evaluated before a later arg writes its source.
    if take2(*p, bump(p)) != 2107
        return 7
    if x.count != 55
        return 8
    # a local, moved in
    var z: Big = big_make(3)
    if scribble(z) != 3 + 4 + 6
        return 9
    return 42
"""
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_struct_params_run_at_O2(ritz1_bin, tmp_path, compiler):
    ll = _ll(compiler, tmp_path, "run", RUN)
    assert "byval(" in ll.read_text(), "the byval lowering did not engage"
    obj = _o2_object(ll)
    _assert_no_libc_mem(obj)
    exe = tmp_path / f"run_{compiler}"
    assert _link_run([obj], exe, with_start=(compiler == "ritz1")) == 42


# --- function pointers ------------------------------------------------------
#
# A `fn(Big) -> i32` value points at a function whose physical signature is
# byval, so the fn-pointer TYPE must be byval too, and so must every indirect
# call through it.  Before this, `apply(take, @x)` bitcast @take to a
# first-class `i32 (%Big)*` and the indirect call passed %Big in registers,
# which the byval callee read as a pointer.

FNPTR = (
    MID
    + """
fn take(b: Big) -> i32
    return total(@b)

fn apply(f: fn(Big) -> i32, p: *Big) -> i32
    return f(*p)

pub fn main() -> i32
    var x: Big = big_make(5)
    if apply(take, @x) != 21
        return 1
    let g: fn(Big) -> i32 = take
    let p: *Big = @x
    if g(*p) != 21
        return 2
    return 42
"""
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_param_fn_pointer_is_byval(ritz1_bin, tmp_path, compiler):
    text = _ll(compiler, tmp_path, "fnptr", FNPTR).read_text()
    hdr = _header(text, "define", "apply")
    indirect = [
        line for line in text.splitlines()
        if re.search(r"call i32 %", line) and "Big" in line
    ]
    assert indirect, f"no indirect call taking %Big:\n{text[-3000:]}"
    for line in indirect:
        assert re.search(BYVAL_BIG, line), f"indirect call is not byval:\n{line}"
    assert not re.search(rf"i32 \({BIG_T}\)\*", text), (
        f"a fn-pointer type still takes %Big first-class:\n{hdr}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_param_fn_pointer_runs_at_O2(ritz1_bin, tmp_path, compiler):
    ll = _ll(compiler, tmp_path, "fnptr_run", FNPTR)
    obj = _o2_object(ll)
    _assert_no_libc_mem(obj)
    exe = tmp_path / f"fnptr_{compiler}"
    assert _link_run([obj], exe, with_start=(compiler == "ritz1")) == 42


# --- ABI interop: ritz0 <-> ritz1, and both <-> C ---------------------------

C_BIG = """\
struct Row { int id; char name[32]; char pat[128]; int a; int b; };
struct Big { struct Row rows[4]; int count; };
"""

# C callee: what clang does for a C `struct Big` param is the ABI to match.
C_CALLEE = (
    C_BIG
    + """\
int c_take(struct Big b) { return b.count * 10 + b.rows[2].a; }
"""
)

# C caller of a Ritz callee.  A global avoids a libc memset for the zeroing.
C_CALLER = (
    C_BIG
    + """\
extern int r_take(struct Big b);
static struct Big g;
int c_call(void) { g.count = 4; g.rows[2].a = 2; return r_take(g); }
"""
)

# The Ritz side that calls a by-value extern.  Linked with C_CALLEE (c_take)
# or with the other compiler's R_DEFINES (r_take).
R_CALLS = (
    MID
    + """
extern fn {callee}(b: Big) -> i32

pub fn main() -> i32
    var b: Big = big_make(4)
    b.rows[2].a = 2
    let p: *Big = @b
    let r = {callee}(*p)
    # The callee's copy is its own; ours is untouched.
    if b.count != 4
        return 1
    return r
"""
)

# The Ritz callee, called by C_CALLER or by the other compiler's R_CALLS.
R_DEFINES = (
    MID
    + """
pub fn r_take(b: Big) -> i32
    var c: Big = b
    c.count = 0
    return b.count * 10 + b.rows[2].a
"""
)

# Ritz program whose main calls the C caller (which calls r_take back).
R_DEFINES_MAIN = (
    R_DEFINES
    + """
extern fn c_call() -> i32

pub fn main() -> i32
    return c_call()
"""
)


def _c_object(tmp_path: Path, name: str, src: str) -> Path:
    c = tmp_path / f"{name}.c"
    c.write_text(src)
    obj = tmp_path / f"{name}.o"
    r = _clang_bounded(
        ["-c", "-O2", "-ffreestanding", "-fno-builtin", str(c), "-o", str(obj)],
        tmp_path,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    _assert_no_libc_mem(obj)
    return obj


def _ritz_obj(compiler: str, tmp_path: Path, name: str, program: str) -> Path:
    obj = _o2_object(_ll(compiler, tmp_path, f"{name}_{compiler}", program))
    _assert_no_libc_mem(obj)
    return obj


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ritz_caller_links_c_callee(ritz1_bin, tmp_path, compiler):
    r_obj = _ritz_obj(
        compiler, tmp_path, "calls_c", R_CALLS.replace("{callee}", "c_take")
    )
    c_obj = _c_object(tmp_path, "c_callee", C_CALLEE)
    exe = tmp_path / f"calls_c_{compiler}"
    assert _link_run([r_obj, c_obj], exe, with_start=(compiler == "ritz1")) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_c_caller_links_ritz_callee(ritz1_bin, tmp_path, compiler):
    r_obj = _ritz_obj(compiler, tmp_path, "defines", R_DEFINES_MAIN)
    c_obj = _c_object(tmp_path, "c_caller", C_CALLER)
    exe = tmp_path / f"c_calls_{compiler}"
    assert _link_run([r_obj, c_obj], exe, with_start=(compiler == "ritz1")) == 42


@pytest.mark.integration
@pytest.mark.parametrize(("caller", "callee"), [("ritz0", "ritz1"), ("ritz1", "ritz0")])
def test_ritz0_and_ritz1_link_by_value_param(ritz1_bin, tmp_path, caller, callee):
    """FC_CALLER / FC_CALLEE for params: each compiler's caller against the
    other compiler's callee."""
    caller_obj = _ritz_obj(
        caller, tmp_path, "calls", R_CALLS.replace("{callee}", "r_take")
    )
    callee_obj = _ritz_obj(callee, tmp_path, "defines", R_DEFINES)
    exe = tmp_path / f"{caller}_calls_{callee}"
    assert (
        _link_run([caller_obj, callee_obj], exe, with_start=(caller == "ritz1")) == 42
    )


def test_c_reference_abi_is_byval_align_8(tmp_path):
    """Pin the target: clang passes C `struct Big` as `ptr byval align 8`."""
    c = tmp_path / "ref.c"
    c.write_text(C_CALLEE)
    r = _clang_bounded(["-S", "-emit-llvm", "-O0", str(c), "-o", "-"], tmp_path)
    assert r.returncode == 0, r.stderr
    hdr = _header(r.stdout, "define", "c_take")
    assert re.search(r"byval\(%struct\.Big\) align 8", hdr), hdr
