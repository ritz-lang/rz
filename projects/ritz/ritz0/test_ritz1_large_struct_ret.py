"""AGAST #1730: ritz1 returns large structs through an sret pointer.

THE DEFECT

ritz1 returned every struct as a first-class LLVM aggregate:

    %v = load %TokenDefs, ptr %slot
    ret %TokenDefs %v

For ritzlib/lang/tokens.ritz's `tokendefs_new` that value is the 22 KB
`%TokenDefs = {[128 x %TokenDef], i32}`.  At -O2, InstCombine unpacks such a
load into one scalar per leaf (~21k), and clang then grows past 13 GB.  That
broke every ci-local gate from b6dad04 on, because
test_printers_output_is_byte_exact[ritz1-*] compiles lang.tokens with ritz1.
ritz0 emits the same `ret`, but its function is `internal` and unused, so it
is deleted before InstCombine ever sees it.

THE FIX

A function whose struct return is >= 256 bytes is now defined
`define void @f(ptr sret(%T) %ret.sret, ...)`.  Every `ret` site fills the
sret slot with `llvm.memcpy` from a pointer and emits `ret void`; no
first-class `%T` value reaches the return.  Every call site to such a
function passes a fresh `alloca %T` as the sret argument.

LLVM already lowers a first-class return this large to a hidden pointer in
the first integer argument register (x86-64 SysV), so the change is
ABI-identical: ritz0 objects and ritz1 objects still link against each
other.  The interop tests below link hand-written first-class-ABI IR against
ritz1's sret IR in both directions to prove it.

Every clang -O2 run here is bounded by RLIMIT_AS and a timeout: an unbounded
clang on the old IR takes the host down.
"""

import os
import resource
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import (  # noqa: F401
    RITZ0,
    RITZ1_BIN,
    RITZ_ROOT,
    RITZ_START,
    ritz1_bin,
)

# clang on ritz0's IR for tokens.ritz takes ~0.1 s at -O2.  20 s and 2 GB are
# two orders of magnitude of headroom, and still turn the old hang into a
# fast, host-safe failure.
O2_TIMEOUT_S = 20
O2_MEM_BYTES = 2 * 1024 * 1024 * 1024


def _limit_mem() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (O2_MEM_BYTES, O2_MEM_BYTES))


def _clang_bounded(args: list, cwd: Path) -> subprocess.CompletedProcess:
    """Run clang under a hard address-space cap and wall-clock timeout.

    A timeout is reported as a failed CompletedProcess (returncode -9), so the
    assertion message names the bound rather than raising out of the test.
    """
    try:
        return subprocess.run(
            ["clang", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=O2_TIMEOUT_S,
            preexec_fn=_limit_mem,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args, -9, "", f"clang exceeded the {O2_TIMEOUT_S}s bound"
        )


def _ritz1_ll(tmp_path: Path, name: str, program: str) -> Path:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    return _ritz1_ll_file(tmp_path, name, src)


def _ritz1_ll_file(tmp_path: Path, name: str, src: Path) -> Path:
    ll = tmp_path / f"{name}_ritz1.ll"
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return ll


def _ritz0_ll(tmp_path: Path, name: str, program: str) -> Path:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_ritz0.ll"
    comp = subprocess.run(
        ["python3", str(RITZ0), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz0 failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return ll


def _o2_object(ll: Path) -> Path:
    obj = ll.with_suffix(".o")
    r = _clang_bounded(
        ["-c", "-O2", "-Wno-override-module", str(ll), "-o", str(obj)], ll.parent
    )
    assert r.returncode == 0, (
        f"clang -O2 on {ll.name} failed or blew the "
        f"{O2_TIMEOUT_S}s / {O2_MEM_BYTES >> 20} MB bound:\n{r.stderr[-2000:]}"
    )
    return obj


# Ritz links -nostdlib: a large llvm.memcpy/memset lowers to a libc call,
# which then fails to link.  The sret copy must not introduce one.
LIBC_MEM = {"memcpy", "memmove", "memset", "bcmp", "memcmp"}


def _assert_no_libc_mem(obj: Path) -> None:
    nm = subprocess.run(["nm", "-u", str(obj)], capture_output=True, text=True)
    assert nm.returncode == 0, nm.stderr
    undef = {line.split()[-1] for line in nm.stdout.splitlines() if line.strip()}
    assert not (undef & LIBC_MEM), f"{obj.name} references libc: {undef & LIBC_MEM}"


def _link_run(objs: list, exe: Path, with_start: bool) -> int:
    cmd = ["clang", "-nostdlib", "-o", str(exe)]
    if with_start:
        cmd.append(str(RITZ_START))
    cmd += [str(o) for o in objs]
    link = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert link.returncode == 0, f"link failed for {exe.name}:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _define_line(ll: Path, fn: str) -> str:
    for line in ll.read_text().splitlines():
        if line.startswith("define") and f"@{fn}(" in line:
            return line
    raise AssertionError(f"no define for @{fn} in {ll.name}")


# --- the 22 KB shape of tokens.ritz -----------------------------------------

BIG_DECLS = """\
struct Row
    id: i32
    name: [32]u8
    pat: [128]u8
    a: i32
    b: i32

struct Big
    rows: [{n}]Row
    count: i32

fn big_new() -> Big
    return Big {{
        rows: [Row {{ id: 0, name: [0; 32], pat: [0; 128], a: 0, b: 0 }}; {n}],
        count: 0
    }}
"""

# 128 rows: the exact size of %TokenDefs (22020 bytes).
HUGE = BIG_DECLS.format(n=128)

# Each case is a callee-side return path of emit_return / the fn-body tail.
HUGE_CASES = {
    # `return T { .. }` (emit_return, struct-literal arm)
    "ret_literal": HUGE,
    # `return local` (emit_return, identifier arm)
    "ret_local": HUGE
    + """
fn big_counted(n: i32) -> Big
    var b: Big = Big {
        rows: [Row { id: 0, name: [0; 32], pat: [0; 128], a: 0, b: 0 }; 128],
        count: 0
    }
    b.count = n
    return b
""",
    # `return *p` (emit_return, deref arm)
    "ret_deref": HUGE
    + """
fn big_copy(p: *Big) -> Big
    return *p
""",
    # `return f()` (emit_return, generic-expression arm forwarding an sret call)
    "ret_forward_call": HUGE
    + """
fn big_wrap() -> Big
    return big_new()
""",
    # A `return` nested in an `if`, next to a fall-through return.
    "ret_in_branch": HUGE
    + """
fn big_pick(n: i32, p: *Big) -> Big
    if n > 0
        return big_new()
    return *p
""",
    # impl method returning a large struct (emit_impl_method header + ret)
    "ret_method": HUGE
    + """
impl Big
    fn fresh_like(self: @&Big) -> Big
        return big_new()

    fn copied(self: @&Big) -> Big
        return *self
""",
}


@pytest.mark.integration
def test_ritz1_lang_tokens_compiles_at_O2_within_bound(ritz1_bin, tmp_path):  # noqa: F811
    """The ticket repro: ritzlib/lang/tokens.ritz through clang -O2."""
    ll = _ritz1_ll_file(
        tmp_path, "tokens", RITZ_ROOT / "ritzlib" / "lang" / "tokens.ritz"
    )
    _assert_no_libc_mem(_o2_object(ll))


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(HUGE_CASES))
def test_ritz1_huge_struct_return_compiles_at_O2_within_bound(
    ritz1_bin,  # noqa: F811
    tmp_path,
    name,
):
    _assert_no_libc_mem(_o2_object(_ritz1_ll(tmp_path, name, HUGE_CASES[name])))


# --- IR shape ---------------------------------------------------------------

SHAPE = (
    HUGE
    + """
struct Small
    x: i64
    y: i64

fn small_new(v: i64) -> Small
    return Small { x: v, y: v + 1 }

fn big_wrap() -> Big
    return big_new()
"""
)


@pytest.mark.integration
def test_ritz1_large_return_is_sret(ritz1_bin, tmp_path):  # noqa: F811
    ll = _ritz1_ll(tmp_path, "shape", SHAPE)
    hdr = _define_line(ll, "big_new")
    assert " void @big_new(ptr sret(%Big) " in hdr, hdr
    text = ll.read_text()
    assert "ret %Big" not in text, "a large struct is still returned first-class"
    assert "call void @big_new(ptr sret(%Big) " in text, (
        "the caller in big_wrap does not pass an sret slot"
    )


@pytest.mark.integration
def test_ritz1_small_return_is_unchanged(ritz1_bin, tmp_path):  # noqa: F811
    """A 16-byte struct still returns in registers: no ABI change below 256 B."""
    ll = _ritz1_ll(tmp_path, "shape", SHAPE)
    hdr = _define_line(ll, "small_new")
    assert " %Small @small_new(" in hdr and "sret" not in hdr, hdr


# --- behaviour on every call path, with a ritz0 oracle ----------------------

# 4 rows = 692 bytes: well over the sret threshold, small enough that ritz0's
# first-class IR still compiles quickly at -O2, so ritz0 can be the oracle.
MID = BIG_DECLS.format(n=4)

CALL_PATHS = (
    MID
    + """
fn big_with(n: i32) -> Big
    var b: Big = big_new()
    b.count = n
    b.rows[2].a = n + 1
    b.rows[3].name[7] = 9
    return b

fn big_pick(n: i32) -> Big
    if n > 100
        return big_new()
    return big_with(n)

fn big_copy(p: *Big) -> Big
    return *p

impl Big
    fn total(self: @&Big) -> i32
        return self.count + self.rows[2].a + self.rows[3].name[7] as i32

    fn grown(self: @&Big, by: i32) -> Big
        var c: Big = big_with(self.count + by)
        return c

    # i64 param: ritz1's static-method path does not narrow call args to the
    # param width (AGAST #1733), and this test is about the return.
    fn made(n: i64) -> Big
        return big_with(n as i32)

pub fn main() -> i32
    var x: Big = big_pick(10)
    if x.total() != 30
        return 1
    let y = big_with(3)
    if y.total() != 16
        return 2
    x = big_with(x.count + y.count)
    if x.total() != 36
        return 3
    var z: Big = x.grown(1)
    if z.total() != 38
        return 4
    var w: Big = Big.made(5)
    if w.total() != 20
        return 5
    var v: Big = big_copy(@w)
    if v.total() != 20
        return 6
    return 42
"""
)


@pytest.mark.integration
def test_ritz0_oracle_call_paths(tmp_path):
    obj = _o2_object(_ritz0_ll(tmp_path, "paths", CALL_PATHS))
    assert _link_run([obj], tmp_path / "paths_ritz0", with_start=False) == 42


@pytest.mark.integration
def test_ritz1_every_call_path_passes_sret(ritz1_bin, tmp_path):  # noqa: F811
    """Every call to an sret fn is `call void @f(ptr sret(%T) ...)`.

    A leftover first-class `call %Big @f(...)` still RUNS on x86-64 (LLVM
    lowers it to the same hidden pointer) and links, so only the IR shape
    shows that a call path missed the sret lowering. One line per path:
    direct, method fallback (x.grown), static method (Big.made).
    """
    text = _ritz1_ll(tmp_path, "paths", CALL_PATHS).read_text()
    for callee in ("big_pick", "big_with", "Big_grown", "Big_made", "big_copy"):
        assert f"call void @{callee}(ptr sret(%Big) " in text, (
            f"the call to @{callee} does not pass an sret slot"
        )
    assert "call %Big " not in text, "a call still returns %Big first-class"


@pytest.mark.integration
def test_ritz1_extern_declare_is_sret(ritz1_bin, tmp_path):  # noqa: F811
    """An extern large-struct fn is declared `void`, matching its sret calls."""
    text = _ritz1_ll(tmp_path, "calls_ext", RITZ1_CALLS_EXT).read_text()
    assert "declare void @ext_big(" in text, text[-1500:]
    assert "declare %Big " not in text
    assert "call void @ext_big(ptr sret(%Big) " in text


@pytest.mark.integration
def test_ritz1_call_paths_run_at_O2(ritz1_bin, tmp_path):  # noqa: F811
    """Direct, untyped-let, reassignment, chained, branch, method,
    static-method and deref-return calls all agree with ritz0."""
    ll = _ritz1_ll(tmp_path, "paths", CALL_PATHS)
    assert "sret(%Big)" in ll.read_text(), "the sret lowering did not engage"
    obj = _o2_object(ll)
    assert _link_run([obj], tmp_path / "paths_ritz1", with_start=True) == 42


# --- ABI interop with first-class-return objects (ritz0's convention) -------

# %Big for MID: 4 x {i32, [32 x i8], [128 x i8], i32, i32} + i32.
FC_TYPES = """\
%Row = type {i32, [32 x i8], [128 x i8], i32, i32}
%Big = type {[4 x %Row], i32}
"""

# A callee using the first-class (ritz0) convention, called from ritz1.
FC_CALLEE = (
    FC_TYPES
    + """\
define %Big @ext_big(i32 %n) {
entry:
  %s = alloca %Big
  call void @llvm.memset.p0.i64(ptr %s, i8 0, i64 692, i1 false)
  %c = getelementptr %Big, ptr %s, i32 0, i32 1
  store i32 %n, ptr %c
  %v = load %Big, ptr %s
  ret %Big %v
}
declare void @llvm.memset.p0.i64(ptr, i8, i64, i1)
"""
)

RITZ1_CALLS_EXT = (
    MID
    + """
extern fn ext_big(n: i32) -> Big

pub fn main() -> i32
    var b: Big = ext_big(41)
    return b.count + 1
"""
)

# A caller using the first-class convention, calling a ritz1 sret callee.
FC_CALLER = (
    FC_TYPES
    + """\
declare %Big @big_make(i32)
define i32 @main() {
entry:
  %v = call %Big @big_make(i32 40)
  %c = extractvalue %Big %v, 1
  %r = add i32 %c, 2
  ret i32 %r
}
"""
)

RITZ1_DEFINES = (
    MID
    + """
pub fn big_make(n: i32) -> Big
    var b: Big = big_new()
    b.count = n
    return b
"""
)


def _fc_object(tmp_path: Path, name: str, ir: str) -> Path:
    ll = tmp_path / f"{name}.ll"
    ll.write_text(ir)
    return _o2_object(ll)


@pytest.mark.integration
def test_ritz1_sret_caller_links_first_class_callee(ritz1_bin, tmp_path):  # noqa: F811
    ritz1_obj = _o2_object(_ritz1_ll(tmp_path, "calls_ext", RITZ1_CALLS_EXT))
    fc_obj = _fc_object(tmp_path, "fc_callee", FC_CALLEE)
    exe = tmp_path / "calls_ext"
    assert _link_run([ritz1_obj, fc_obj], exe, with_start=True) == 42


@pytest.mark.integration
def test_ritz1_sret_callee_links_first_class_caller(ritz1_bin, tmp_path):  # noqa: F811
    ritz1_obj = _o2_object(_ritz1_ll(tmp_path, "defines", RITZ1_DEFINES))
    fc_obj = _fc_object(tmp_path, "fc_caller", FC_CALLER)
    # FC_CALLER defines `main` directly, so no ritz start object; link a tiny
    # _start that exits with main's result.
    start = tmp_path / "start.ll"
    start.write_text(
        "declare i32 @main()\n"
        "define void @_start() {\n"
        "  %r = call i32 @main()\n"
        "  %e = sext i32 %r to i64\n"
        '  call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"'
        "(i64 60, i64 %e)\n"
        "  unreachable\n"
        "}\n"
    )
    start_obj = _o2_object(start)
    exe = tmp_path / "defines"
    assert _link_run([ritz1_obj, fc_obj, start_obj], exe, with_start=False) == 42
