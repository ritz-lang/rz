"""AGAST #1879: the low-level features a kernel needs, in every compiler.

LANGUAGE_SPEC §18.4-§18.6, §5.3 and §17.7 specify them; this pins each one on
ritz0, ritz1 and ritz1_selfhosted, both as IR (the instruction LLVM must see)
and as behaviour (a linked program's exit code):

* volatile_load / volatile_store  -> `load volatile` / `store volatile`
* atomic_* and fence()            -> `load atomic` / `store atomic` /
                                     `atomicrmw` / `cmpxchg` / `fence`,
                                     all seq_cst
* extern var NAME: T              -> `@NAME = external global T`
* [[callconv = "win64"]]          -> `win64cc` on a fn's define / declare /
                                     call, and on calls through a value of a
                                     fn-type alias that carries it
* [[packed]] (already #1847)      -> a `<{ ... }>` struct type

The win64 tests link against hand-written IR that uses the Microsoft x64
convention, so a compiler that drops `win64cc` passes the arguments in the
wrong registers and the program returns the wrong value: the exit code, not
only the IR text, is what fails.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration


def _compile(compiler, tmp_path, src, name="t"):
    path = tmp_path / f"{name}.ritz"
    path.write_text(src)
    ll = tmp_path / f"{name}_{compiler}.ll"
    if ll.exists():
        ll.unlink()
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env,
                         timeout=300), ll
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


def _ir(compiler, tmp_path, src, name="t"):
    proc, ll = _compile(compiler, tmp_path, src, name)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {name}:\n{out}"
    return ll


def _run(compiler, tmp_path, src, extra_ll=None, name="t"):
    """Compile, link (with an optional hand-written .ll), run; return the exit code."""
    ll = _ir(compiler, tmp_path, src, name)
    objs = [str(ll)]
    if extra_ll is not None:
        helper = tmp_path / "helper.ll"
        helper.write_text(extra_ll)
        objs.append(str(helper))
    if compiler != "ritz0":
        objs.insert(0, str(RITZ_START))
    exe = tmp_path / f"{name}_{compiler}"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    return run.returncode


def _rejected(compiler, tmp_path, src, needle, where):
    proc, _ = _compile(compiler, tmp_path, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted:\n{src}\n{out}"
    assert needle in out, f"{compiler}: rejected, but not with {needle!r}:\n{out}"
    assert re.search(rf"{re.escape(where)}\b", out), (
        f"{compiler}: error not located at {where}:\n{out}")


# --- volatile ---------------------------------------------------------------

VOLATILE = """\
var g_reg: u32 = 0

fn main() -> i32
    var b: u8 = 0
    var h: i16 = 0
    var w: u64 = 0
    let rp: *u32 = @g_reg as *u32
    let bp: *u8 = @b as *u8
    let hp: *i16 = @h as *i16
    let wp: *u64 = @w as *u64
    volatile_store(rp, 0x12345678)
    volatile_store(bp, 200)
    volatile_store(hp, -300)
    volatile_store(wp, 1 << 40)
    let r: u32 = volatile_load(rp)
    let bb: u8 = volatile_load(bp)
    let hh: i16 = volatile_load(hp)
    let ww: u64 = volatile_load(wp)
    if r != 0x12345678
        return 1
    if bb != 200
        return 2
    if hh != -300
        return 3
    if ww != 1 << 40
        return 4
    # Each access is its own instruction: two loads, two values.
    volatile_store(rp, 7)
    let first: u32 = volatile_load(rp)
    volatile_store(rp, 9)
    let second: u32 = volatile_load(rp)
    (first * 10 + second) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_volatile_ir(compiler, tmp_path):
    ir = _ir(compiler, tmp_path, VOLATILE).read_text()
    # Pointer operands are `ptr` (ritz1) or typed `i32*` (ritz0): match either.
    for width in ("i8", "i16", "i32", "i64"):
        assert re.search(rf"load volatile {width}, ", ir), f"{compiler}: no volatile {width} load"
        assert re.search(rf"store volatile {width} ", ir), f"{compiler}: no volatile {width} store"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_volatile_runs(compiler, tmp_path):
    assert _run(compiler, tmp_path, VOLATILE) == 79


# --- atomics ----------------------------------------------------------------

ATOMICS = """\
var g_lock: u32 = 0
var g_count: i64 = 0

fn spin_lock()
    while atomic_xchg(@g_lock as *u32, 1) != 0
        pass

fn spin_unlock()
    atomic_store(@g_lock as *u32, 0)

fn main() -> i32
    let p: *i64 = @g_count as *i64
    atomic_store(p, 5)
    if atomic_load(p) != 5
        return 1
    if atomic_xchg(p, 9) != 5
        return 2
    if atomic_fetch_add(p, 3) != 9
        return 3
    if atomic_fetch_sub(p, 2) != 12
        return 4
    # cmpxchg returns the old value: equal to `expected` iff it stored.
    if atomic_cmpxchg(p, 10, 0xF0) != 10
        return 5
    if atomic_cmpxchg(p, 10, 77) != 0xF0
        return 6
    if atomic_fetch_and(p, 0x3C) != 0xF0
        return 7
    if atomic_fetch_or(p, 0x01) != 0x30
        return 8
    if atomic_fetch_xor(p, 0x11) != 0x31
        return 9
    fence()
    # Narrow and signed pointees: the old value comes back sign-extended.
    var s: i8 = -3
    let sp: *i8 = @s as *i8
    if atomic_xchg(sp, 4) != -3
        return 10
    if atomic_fetch_add(sp, -10) != 4
        return 11
    if s != -6
        return 12
    spin_lock()
    let held: u32 = atomic_load(@g_lock as *u32)
    spin_unlock()
    if held != 1 or g_lock != 0
        return 13
    atomic_load(p) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_atomics_ir(compiler, tmp_path):
    ir = _ir(compiler, tmp_path, ATOMICS).read_text()
    # Pointer operands are `ptr` (ritz1) or typed `i64*` (ritz0): `[^,]+`.
    for op in ("xchg", "add", "sub", "and", "or", "xor"):
        assert re.search(rf"atomicrmw {op} [^,]+, i\d+ \S+ seq_cst", ir), \
            f"{compiler}: no seq_cst atomicrmw {op}"
    assert re.search(r"atomicrmw xchg [^,]+, i32 ", ir), f"{compiler}: xchg on *u32 not i32"
    assert re.search(r"atomicrmw add [^,]+, i8 ", ir), f"{compiler}: fetch_add on *i8 not i8"
    assert re.search(r"cmpxchg [^,]+, i64 [^,]+, i64 [^,]+ seq_cst seq_cst", ir), \
        f"{compiler}: no seq_cst cmpxchg i64"
    assert re.search(r"load atomic i64, [^,]+ seq_cst, align 8", ir), f"{compiler}: no atomic load"
    assert re.search(r"store atomic i32 [^,]+, [^,]+ seq_cst, align 4", ir), \
        f"{compiler}: no atomic store"
    assert re.search(r"^\s*fence seq_cst", ir, re.M), f"{compiler}: no fence"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_atomics_run(compiler, tmp_path):
    assert _run(compiler, tmp_path, ATOMICS) == 0x20


# --- extern data symbols ----------------------------------------------------

EXTERN_VAR = """\
extern var ext_count: i64
extern var __region_start: u8
extern var __region_end: u8

fn main() -> i32
    let size: i64 = @__region_end as i64 - @__region_start as i64
    ext_count = ext_count + size
    ext_count as i32
"""

EXTERN_VAR_DEFS = """\
@ext_count = global i64 30
@__region_start = global [12 x i8] zeroinitializer
@__region_end = alias i8, getelementptr (i8, ptr @__region_start, i64 12)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_extern_var_ir(compiler, tmp_path):
    ir = _ir(compiler, tmp_path, EXTERN_VAR).read_text()
    assert re.search(r"^@\"?ext_count\"? = external global i64\s*$", ir, re.M), ir
    assert re.search(r"^@\"?__region_start\"? = external global i8\s*$", ir, re.M), ir
    assert not re.search(r"^@\"?ext_count\"? = (?!external)", ir, re.M), \
        f"{compiler} defined an extern var:\n{ir}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_extern_var_links(compiler, tmp_path):
    assert _run(compiler, tmp_path, EXTERN_VAR, EXTERN_VAR_DEFS) == 42


# --- foreign calling convention ---------------------------------------------

# A UEFI-shaped callee: Microsoft x64, five arguments (the fifth on the
# stack), reached both directly and through a fn pointer read from a table.
WIN64_DEFS = """\
define win64cc i64 @w_mix(i64 %a, i64 %b, i64 %c, i64 %d, i64 %e) {
  %ab = mul i64 %a, 10000
  %bb = mul i64 %b, 1000
  %cb = mul i64 %c, 100
  %db = mul i64 %d, 10
  %s1 = add i64 %ab, %bb
  %s2 = add i64 %s1, %cb
  %s3 = add i64 %s2, %db
  %s4 = add i64 %s3, %e
  ret i64 %s4
}

@w_table = global ptr @w_mix

declare win64cc i64 @r_cb(i64, i64, i64, i64, i64)

define i64 @drive_cb() {
  %r = call win64cc i64 @r_cb(i64 1, i64 2, i64 3, i64 4, i64 5)
  ret i64 %r
}
"""

WIN64 = """\
[[callconv = "win64"]]
type WinFn5 = fn(i64, i64, i64, i64, i64) -> i64

[[callconv = "win64"]]
extern fn w_mix(a: i64, b: i64, c: i64, d: i64, e: i64) -> i64

extern fn drive_cb() -> i64

extern var w_table: u64

# Called by drive_cb with the Microsoft convention (pub: another object calls it).
[[callconv = "win64"]]
pub fn r_cb(a: i64, b: i64, c: i64, d: i64, e: i64) -> i64
    a * 10000 + b * 1000 + c * 100 + d * 10 + e

fn main() -> i32
    if w_mix(1, 2, 3, 4, 5) != 12345
        return 1
    let f: WinFn5 = w_table as WinFn5
    if f(5, 4, 3, 2, 1) != 54321
        return 2
    if drive_cb() != 12345
        return 3
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_win64_ir(compiler, tmp_path):
    ir = _ir(compiler, tmp_path, WIN64).read_text()
    assert re.search(r"^declare (external )?win64cc i64 @\"?w_mix\"?\(", ir, re.M), f"{compiler}: w_mix decl"
    assert re.search(r"^define .*win64cc i64 @\"?r_cb\"?\(", ir, re.M), f"{compiler}: r_cb define"
    assert re.search(r"call win64cc i64 @\"?w_mix\"?\(", ir), f"{compiler}: direct call"
    assert re.search(r"call win64cc i64 %", ir), f"{compiler}: call through WinFn5"
    # A plain C fn keeps the default convention.
    assert re.search(r"call i64 @\"?drive_cb\"?\(", ir), f"{compiler}: drive_cb not ccc"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_win64_runs(compiler, tmp_path):
    assert _run(compiler, tmp_path, WIN64, WIN64_DEFS) == 0


# AGAST #2120: every callee expression whose type is the alias carries its
# convention, not only a typed local. `(p as EfiFn)(..)` is the form harland's
# boot wants; the others are the remaining ways a value of the alias reaches
# a call.
WIN64_CALLEE_PRELUDE = """\
[[callconv = "win64"]]
type WinFn5 = fn(i64, i64, i64, i64, i64) -> i64

struct Tbl
    f: WinFn5

extern var w_table: u64

fn get_fn() -> WinFn5
    w_table as WinFn5
"""

WIN64_CALLEES = {
    "cast": """\
fn go(p: u64) -> i64
    (p as WinFn5)(1, 2, 3, 4, 5)
""",
    "field_via_ptr": """\
fn go(p: u64) -> i64
    var t: Tbl
    t.f = p as WinFn5
    let tp: *Tbl = @t
    (tp.f)(1, 2, 3, 4, 5)
""",
    "field": """\
fn go(p: u64) -> i64
    var t: Tbl
    t.f = p as WinFn5
    (t.f)(1, 2, 3, 4, 5)
""",
    "array_element": """\
fn go(p: u64) -> i64
    var a: [2]WinFn5
    a[1] = p as WinFn5
    a[1](1, 2, 3, 4, 5)
""",
    "returned": """\
fn go(p: u64) -> i64
    get_fn()(1, 2, 3, 4, 5)
""",
    "paren_local": """\
fn go(p: u64) -> i64
    let f: WinFn5 = p as WinFn5
    (f)(1, 2, 3, 4, 5)
""",
}

# WIN64_DEFS without drive_cb, whose r_cb these programs do not define.
WIN64_CALLEE_DEFS = WIN64_DEFS[:WIN64_DEFS.index("declare win64cc i64 @r_cb")]

WIN64_CALLEE_MAIN = """
fn main() -> i32
    if go(w_table) != 12345
        return 1
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(WIN64_CALLEES))
def test_win64_callee_forms_ir(compiler, form, tmp_path):
    src = WIN64_CALLEE_PRELUDE + WIN64_CALLEES[form] + WIN64_CALLEE_MAIN
    ir = _ir(compiler, tmp_path, src).read_text()
    # The one call through a pointer is the WinFn5 call: it must be win64cc.
    indirect = re.findall(r"call (?:\w+ )*?[^\s@%]+ %[^\s(]+\(", ir)
    assert indirect, f"{compiler}/{form}: no indirect call:\n{ir}"
    assert all("win64cc" in c for c in indirect), \
        f"{compiler}/{form}: indirect call without win64cc: {indirect}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(WIN64_CALLEES))
def test_win64_callee_forms_run(compiler, form, tmp_path):
    # SysV registers into the MS x64 w_mix give a value other than 12345.
    src = WIN64_CALLEE_PRELUDE + WIN64_CALLEES[form] + WIN64_CALLEE_MAIN
    assert _run(compiler, tmp_path, src, WIN64_CALLEE_DEFS) == 0


# --- [[packed]] IR (the #1847 feature, pinned here for the ticket) ----------

PACKED = """\
[[packed]]
struct GdtPointer
    limit: u16
    base: u64

fn main() -> i32
    var p: GdtPointer
    p.limit = 7
    p.base = 9
    (p.limit + p.base as u16) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_packed_ir(compiler, tmp_path):
    ir = _ir(compiler, tmp_path, PACKED).read_text()
    # ritz0 module-qualifies the name (`%"struct.ritz_module_1.GdtPointer"`).
    assert re.search(r"%\"?[\w.]*\bGdtPointer\"? = type <\{ ?i16, ?i64 ?\}>", ir), ir


# --- rejections -------------------------------------------------------------

REJECTS = {
    "volatile_struct": ("""\
struct S
    a: i64

fn main() -> i32
    var s: S = S { a: 1 }
    let p: *S = @s as *S
    let v: S = volatile_load(p)
    0
""", "needs a pointer to an integer", "t.ritz:7"),
    "atomic_arity": ("""\
fn main() -> i32
    var x: i64 = 0
    atomic_fetch_add(@x as *i64)
    0
""", "atomic_fetch_add takes 2 arguments", "t.ritz:3"),
    "callconv_unknown": ("""\
[[callconv = "fastcall"]]
fn f() -> i64
    0

fn main() -> i32
    0
""", "unknown calling convention 'fastcall'", "t.ritz:1"),
    "callconv_on_struct": ("""\
[[callconv = "win64"]]
struct S
    a: i64

fn main() -> i32
    0
""", "attribute 'callconv' applies to", "t.ritz:1"),
    "callconv_alias_not_fn": ("""\
[[callconv = "win64"]]
type N = i64

fn main() -> i32
    0
""", "attribute 'callconv' applies to", "t.ritz:1"),
    "callconv_bare": ("""\
[[callconv]]
fn f() -> i64
    0

fn main() -> i32
    0
""", "attribute 'callconv' needs a value", "t.ritz:1"),
    "extern_var_init": ("""\
extern var x: i64 = 5

fn main() -> i32
    0
""", "extern var cannot have an initializer", "t.ritz:1"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(REJECTS))
def test_rejected(compiler, case, tmp_path):
    src, needle, where = REJECTS[case]
    _rejected(compiler, tmp_path, src, needle, where)
