"""AGAST #1736: ritz0 returns large structs through an sret pointer, and a
`var` initialised from such a call is filled in place.

THE DEFECT

tome_cli.ritz does `var client: TomeClient = client_new()`, where
TomeClient is the 8 KB `{i32, i32, [8192 x i8], i32}`. ritz0 emitted

    %v = call %TomeClient @client_new()
    store %TomeClient %v, %TomeClient* %client.addr
    call void @llvm.dbg.declare(metadata %TomeClient* %client.addr, ...)

The first-class 8 KB value is split into one SelectionDAG value per byte, and
the debug-declared alloca it is stored into is tracked fragment by fragment.
`clang -c -O2` on tome_cli's 142 KB .ll took 6.5 GB and 160 s, and under
build.py's 4096 MiB RLIMIT_AS (#1731) it died in "Live DEBUG_VALUE analysis"
with `LLVM ERROR: out of memory`. Before #1731 the failure was swallowed and
the .ll linked instead. It is the call-site half of #1730, which fixed the
same shape in ritz1.

THE FIX

Same ABI as ritz1 (#1730): a function whose return is a named struct of at
least 256 bytes is `define void @f(%T* sret(%T) %.1, ...)`; its `ret`s store
into the sret pointer; every call passes a slot. A `var` initialised directly
from such a call passes the variable's own alloca as the slot, so no
first-class %T exists at that site at all.

x86-64 SysV already returns an aggregate this large through a hidden pointer
in %rdi, so the change is ABI-identical: objects built before and after link
together. The interop tests check this in both directions.

Every clang -O2 run here is bounded (RLIMIT_AS + timeout).
"""

import os
import re
import resource
import subprocess
import sys
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

sys.path.insert(0, str(RITZ0_DIR))

O2_TIMEOUT_S = 60
O2_MEM_BYTES = 2 * 1024 * 1024 * 1024
OBJ_FLAGS = ["-c", "-O2", "-fPIC", "-ffreestanding", "-fno-builtin",
             "-Wno-override-module"]


def _limit_mem() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (O2_MEM_BYTES, O2_MEM_BYTES))


def _clang_bounded(args: list, cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["clang", *args], cwd=cwd, capture_output=True, text=True,
            timeout=O2_TIMEOUT_S, preexec_fn=_limit_mem)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args, -9, "", f"clang exceeded the {O2_TIMEOUT_S}s bound")


def _ritz0_ll(tmp_path: Path, name: str, program: str, *extra: str) -> Path:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.ll"
    r = run_ritz0(
        [str(src), "-o", str(ll), *extra],
        cwd=tmp_path, env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        timeout=300)
    assert r.returncode == 0 and ll.exists(), (
        f"ritz0 failed on {name}:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return ll


def _o2_object(ll: Path) -> Path:
    obj = ll.with_suffix(".o")
    r = _clang_bounded([*OBJ_FLAGS, str(ll), "-o", str(obj)], ll.parent)
    head = "\n".join(ln for ln in r.stderr.splitlines()
                     if re.search(r"LLVM ERROR|error in backend|Running pass", ln))
    assert r.returncode == 0, (
        f"clang -c -O2 on {ll.name} failed or blew the {O2_TIMEOUT_S}s / "
        f"{O2_MEM_BYTES >> 20} MiB bound:\n{head or r.stderr[-2000:]}")
    return obj


# Ritz links -nostdlib. An sret copy must not turn into a libc memcpy call.
LIBC_MEM = {"memcpy", "memmove", "memset", "bcmp", "memcmp"}


def _assert_no_libc_mem(obj: Path) -> None:
    nm = subprocess.run(["nm", "-u", str(obj)], capture_output=True, text=True)
    assert nm.returncode == 0, nm.stderr
    undef = {ln.split()[-1] for ln in nm.stdout.splitlines() if ln.strip()}
    assert not (undef & LIBC_MEM), f"{obj.name} references libc: {undef & LIBC_MEM}"


def _fn_body(ir: str, fn: str) -> str:
    lines = ir.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("define") and f'@"{fn}"(' in line:
            end = lines.index("}", i)
            return "\n".join(lines[i:end + 1])
    raise AssertionError(f"no define for @{fn}")


def _sig_line(ir: str, kind: str, fn: str) -> str:
    for line in ir.splitlines():
        if line.startswith(kind) and f'@"{fn}"(' in line:
            return line
    raise AssertionError(f"no {kind} for @{fn}")


# --- the tome_cli shape ------------------------------------------------------

# tome_cli.ritz reduced to the construct that blew up: an 8 KB struct
# returned from a function in another module, stored into a debug-declared
# `var`. `extern fn` gives the same `declare` + call that an import does.
TOME_CLI = """\
struct Client
    fd: i32
    port: i32
    buf: [8192]u8
    len: i32

extern fn client_new() -> Client
extern fn client_connect(c: *Client, port: i32) -> i32

fn main() -> i32
    var client: Client = client_new()
    let rc: i32 = client_connect(@client, 7)
    rc
"""


@pytest.mark.integration
def test_tome_cli_shape_compiles_at_O2_within_bound(tmp_path):
    """The ticket repro. Before: LLVM ERROR: out of memory under 2 GiB."""
    obj = _o2_object(_ritz0_ll(tmp_path, "tome_cli_shape", TOME_CLI, "--no-runtime"))
    _assert_no_libc_mem(obj)


@pytest.mark.integration
@pytest.mark.unit
def test_var_init_from_sret_call_fills_the_var_in_place(tmp_path):
    ir = _ritz0_ll(tmp_path, "tome_cli_shape", TOME_CLI, "--no-runtime").read_text()
    body = _fn_body(ir, "main")
    assert re.search(
        r'call void @"client_new"\(%"[^"]+"\* sret\(%"[^"]+"\) %"client\.addr"\)', body), (
        f"client_new() must write straight into client.addr:\n{body}")
    big = re.findall(r'(?:load|store|call) %"struct\.[^"]*Client"[ ,]', body)
    assert not big, f"a first-class %Client value survives in main: {big}"


@pytest.mark.integration
@pytest.mark.unit
def test_extern_large_struct_return_is_declared_sret(tmp_path):
    ir = _ritz0_ll(tmp_path, "tome_cli_shape", TOME_CLI, "--no-runtime").read_text()
    decl = _sig_line(ir, "declare", "client_new")
    assert re.match(r'declare (external )?void @"client_new"\(%"[^"]+"\* sret\(', decl), decl


# --- every call / return path, run end to end -------------------------------

PROGRAM = """\
struct Big
    head: i32
    buf: [300]u8
    tail: i32

struct Small
    a: i32
    b: i32

fn big_make(h: i32, t: i32) -> Big
    var b: Big = Big { head: h, buf: [0; 300], tail: t }
    b.buf[299] = 7
    return b

fn big_fwd(h: i32) -> Big
    return big_make(h, h + 1)

fn big_pick(n: i32) -> Big
    if n > 0
        return big_make(n, 2)
    big_make(0, 3)

fn small_make() -> Small
    Small { a: 1, b: 2 }

fn sum(b: Big) -> i32
    b.head + b.tail + (b.buf[299] as i32)

impl Big
    fn twice(self: @&Big) -> Big
        big_make(self.head * 2, self.tail * 2)

    fn zero() -> Big
        big_make(0, 0)

fn main() -> i32
    var a: Big = big_make(1, 2)
    var b = big_fwd(3)
    let c: Big = big_pick(5)
    var d: Big = a.twice()
    var e: Big = Big.zero()
    let s: Small = small_make()
    e = big_make(9, 9)
    sum(a) + sum(b) + sum(c) + sum(d) + sum(e) + sum(big_pick(0)) + s.a + s.b
"""
# a=1+2+7=10, b=3+4+7=14, c=5+2+7=14, d=2+4+7=13, e (reassigned)=9+9+7=25,
# big_pick(0)=0+3+7=10, s=3 -> 89.
PROGRAM_EXIT = 89


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.parametrize("fn", ["big_make", "big_fwd", "big_pick", "Big_twice", "Big_zero"])
def test_large_struct_return_is_defined_sret(tmp_path, fn):
    ir = _ritz0_ll(tmp_path, "prog", PROGRAM, "--no-runtime").read_text()
    define = _sig_line(ir, "define", fn)
    assert re.match(rf'define (\w+ )*void @"{fn}"\(%"[^"]+"\* sret\(%"[^"]+"\) ', define), define
    body = _fn_body(ir, fn)
    assert "ret void" in body and not re.search(r'ret %"struct', body), body


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.parametrize("fn,callee", [
    ("big_fwd", "big_make"),     # `return f()`
    ("big_pick", "big_make"),    # `return f()` in a branch, and the tail
    ("Big_twice", "big_make"),   # method tail
])
def test_return_of_sret_call_forwards_the_callers_slot(tmp_path, fn, callee):
    """`return f()` hands f the function's own sret pointer: no slot, no
    first-class %T copied from one to the other."""
    body = _fn_body(_ritz0_ll(tmp_path, "prog", PROGRAM, "--no-runtime").read_text(), fn)
    assert re.search(
        rf'call void @"{callee}"\(%"[^"]+"\* sret\(%"[^"]+"\) %"ret\.sret"', body), body
    assert "sret.slot" not in body and not re.search(r'(load|store) %"struct', body), body


@pytest.mark.integration
@pytest.mark.unit
def test_small_struct_return_keeps_first_class_abi(tmp_path):
    ir = _ritz0_ll(tmp_path, "prog", PROGRAM, "--no-runtime").read_text()
    assert re.match(r'define (\w+ )*%"struct\.[^"]*Small" @"small_make"\(\)',
                    _sig_line(ir, "define", "small_make"))


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.parametrize("callee,var", [
    ("big_make", "a"),       # typed var, direct call
    ("big_fwd", "b"),        # inferred var
    ("Big_twice", "d"),      # method call
    ("Big_zero", "e"),       # static method call
])
def test_var_init_paths_pass_the_var_as_sret_slot(tmp_path, callee, var):
    ir = _ritz0_ll(tmp_path, "prog", PROGRAM, "--no-runtime").read_text()
    body = _fn_body(ir, "main")
    assert re.search(
        rf'call void @"{callee}"\(%"[^"]+"\* sret\(%"[^"]+"\) %"{var}\.addr"', body), (
        f"{callee}() must write straight into {var}.addr:\n{body}")


@pytest.mark.integration
@pytest.mark.parametrize("opt", ["-O0", "-O2"])
def test_program_runs_correctly(tmp_path, opt):
    ll = _ritz0_ll(tmp_path, "prog", PROGRAM)
    exe = tmp_path / "prog"
    link = subprocess.run(
        ["clang", opt, "-nostdlib", "-Wno-override-module", str(ll), "-o", str(exe)],
        capture_output=True, text=True, timeout=120, preexec_fn=_limit_mem)
    assert link.returncode == 0, link.stderr[-2000:]
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == PROGRAM_EXIT, f"exit {run.returncode}, want {PROGRAM_EXIT}"


@pytest.mark.integration
def test_program_objects_have_no_libc_mem_refs(tmp_path):
    _assert_no_libc_mem(_o2_object(_ritz0_ll(tmp_path, "prog", PROGRAM, "--no-runtime")))


# --- ABI interop with first-class-return objects -----------------------------

# A first-class-ABI caller and callee for the same %Big, as an object built
# before this change (or by any other producer) would look.
FIRST_CLASS_IR = """\
%Big = type {i32, [300 x i8], i32}

declare %Big @"big_make"(i32, i32)

define i32 @"fc_sum"() {
  %v = call %Big @"big_make"(i32 40, i32 2)
  %h = extractvalue %Big %v, 0
  %b = extractvalue %Big %v, 1, 299
  %t = extractvalue %Big %v, 2
  %b32 = zext i8 %b to i32
  %s1 = add i32 %h, %t
  %s = add i32 %s1, %b32
  ret i32 %s
}

define %Big @"fc_make"(i32 %h) {
  %a = insertvalue %Big zeroinitializer, i32 %h, 0
  %b = insertvalue %Big %a, i8 5, 1, 299
  %c = insertvalue %Big %b, i32 1, 2
  ret %Big %c
}
"""

INTEROP = """\
struct Big
    head: i32
    buf: [300]u8
    tail: i32

extern fn fc_sum() -> i32
extern fn fc_make(h: i32) -> Big

pub fn big_make(h: i32, t: i32) -> Big
    var b: Big = Big { head: h, buf: [0; 300], tail: t }
    b.buf[299] = 7
    return b

fn main() -> i32
    var m: Big = fc_make(30)
    fc_sum() + m.head + m.tail + (m.buf[299] as i32)
"""
# fc_sum: 40 + 2 + 7 = 49 (ritz0 sret callee, first-class caller)
# fc_make(30): 30 + 1 + 5 = 36 (first-class callee, ritz0 sret caller)
INTEROP_EXIT = 85


@pytest.mark.integration
def test_sret_is_abi_compatible_with_first_class_return(tmp_path):
    ritz_ll = _ritz0_ll(tmp_path, "interop", INTEROP)
    fc_ll = tmp_path / "first_class.ll"
    fc_ll.write_text(FIRST_CLASS_IR)
    objs = [_o2_object(ritz_ll), _o2_object(fc_ll)]
    exe = tmp_path / "interop"
    link = subprocess.run(
        ["clang", "-nostdlib", "-o", str(exe), *map(str, objs)],
        capture_output=True, text=True, timeout=120)
    assert link.returncode == 0, link.stderr[-2000:]
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == INTEROP_EXIT, f"exit {run.returncode}, want {INTEROP_EXIT}"


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.parametrize("fn", ["big_make", "Big_twice"])
def test_sret_definition_keeps_freestanding_attrs(tmp_path, fn):
    """`alignstack(16) "no-builtins"` is added by a regex over `define`
    lines. An sret parameter list has parens inside it (`sret(%T)`), which
    the old pattern stopped at. The function lost "no-builtins", and -O2 turned
    its zero-fill into a call to libc memset (AGAST #1313)."""
    ir = _ritz0_ll(tmp_path, "prog", PROGRAM, "--no-runtime").read_text()
    define = _sig_line(ir, "define", fn)
    assert 'alignstack(16) "no-builtins"' in define, define


# --- per-fn IR cache --------------------------------------------------------

@pytest.mark.integration
@pytest.mark.unit
def test_cache_extracts_sret_definitions(tmp_path):
    """The per-fn cache stores each `define` block. It must find sret ones."""
    from emitter_llvmlite import _extract_fn_ir_blocks
    ir = _ritz0_ll(tmp_path, "prog", PROGRAM, "--no-runtime").read_text()
    blocks = _extract_fn_ir_blocks(ir)
    assert "big_make" in blocks and "sret(" in blocks["big_make"], sorted(blocks)


@pytest.mark.unit
def test_cached_sret_body_splices_over_its_declare():
    """The cache splices a cached `define` over the `declare` line. An sret
    declare has parens inside its parameter list (`sret(%T)`), which the
    old `\\([^)]*\\)` pattern could not match. The body was silently left
    out and the link failed with an undefined symbol."""
    from emitter_llvmlite import _splice_cached_ir
    ir = ('%"T" = type {[300 x i8]}\n'
          'declare void @"mk"(%"T"* sret(%"T") %".1", i32 %".2")\n')
    body = ('define void @"mk"(%"T"* sret(%"T") %".1", i32 %".2")\n'
            '{\nentry:\n  ret void\n}')
    out = _splice_cached_ir(ir, {"mk": body})
    assert "declare" not in out and body in out, out
