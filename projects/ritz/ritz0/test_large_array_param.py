"""AGAST #2306 / #3181: large by-value arrays are `ptr byval` / `ptr sret`.

THE DEFECT

Since #2287 (params) and #2302 (returns) both compilers pass and return a
by-value `[N]T` as a first-class `[N x T]`:

    define i32 @g([65536 x i8] %a.arg)          ; and every caller loads it
    define [65536 x i8] @mk(i8 %x.arg)          ; and every caller stores it

LLVM splits a first-class aggregate argument into one scalar per element.
For `fn g(a: [N]u8)`: N = 16384 gives no -O2 result in 60 s, and N = 65536
crashes clang -O0 in X86 instruction selection.  #1739 / #1730 moved large
STRUCT params / returns off the first-class form for the same reason; arrays
never followed.

THE FIX (an ABI change both compilers make together)

A by-value array of at least SRET_MIN_BYTES (256) is passed as
`ptr byval([N x T]) align A` and returned through `ptr sret([N x T])`.  `A` is
the element's natural alignment (1 for u8, 4 for u32, 8 for u64 / pointers):
a byval `align` also promises the pointer the caller passes is that aligned,
and a `[N]u8` local is only 1-aligned.  The x86-64 SysV convention rounds a
byval stack slot up to 8 anyway, so the attribute changes no stack layout.
Smaller arrays keep the first-class form.

Every clang run here is bounded (time and memory): the defect is a hang.
"""

import re
from pathlib import Path

import pytest

from test_ritz1_large_struct_ret import (
    _clang_bounded,
    _link_run,
    _ritz0_ll,
    _ritz1_ll,
)

COMPILERS = ("ritz0", "ritz1")


def _ll(compiler: str, tmp_path: Path, name: str, program: str) -> Path:
    if compiler == "ritz0":
        return _ritz0_ll(tmp_path, name, program)
    return _ritz1_ll(tmp_path, name, program)


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


def _object(ll: Path, opt: str) -> Path:
    obj = ll.with_name(f"{ll.stem}{opt}.o")
    r = _clang_bounded(["-c", opt, "-Wno-override-module", str(ll), "-o", str(obj)], ll.parent)
    assert r.returncode == 0, (
        f"clang {opt} on {ll.name} failed, crashed or blew its bound:\n{r.stderr[-2000:]}"
    )
    return obj


# --- the ticket repro: a 64 KB `[N]u8` param and return ----------------------

HUGE = """\
pub fn g(a: [65536]u8) -> i32
    a[0] as i32 + a[65535] as i32

# The callee owns its copy: writing it must not reach the caller.
pub fn scribble(a: [65536]u8) -> i32
    a[0] = 99
    a[0] as i32

pub fn mk(x: u8) -> [65536]u8
    # Not `[0; N]`: ritz1 zero-fills with llvm.memset, which needs ritzlib.
    var b: [65536]u8 = [7; 65536]
    b[0] = x
    b[65535] = x + 1
    b

pub fn relay(x: u8) -> [65536]u8
    return mk(x)

struct Box
    k: u8

impl Box
    # Instance and static method calls take their own call paths.
    fn take(self: @Box, a: [65536]u8) -> i32
        a[65535] as i32 + self.k as i32

    fn make(x: u8) -> [65536]u8
        mk(x)

    fn made(self: @Box) -> [65536]u8
        mk(self.k)

fn main() -> i32
    var b: [65536]u8 = mk(20)
    if g(b) != 41
        return 1
    if scribble(b) != 99 or b[0] != 20
        return 2
    let c: [65536]u8 = relay(3)
    if c[0] != 3 or c[65535] != 4
        return 3
    if g(mk(5)) != 11
        return 4
    let bx = Box { k: 9 }
    if bx.take(b) != 30
        return 5
    let d: [65536]u8 = Box.make(6)
    let e: [65536]u8 = bx.made()
    if d[65535] != 7 or e[0] != 9
        return 6
    # An indirect call through a fn pointer.
    let gp: fn([65536]u8) -> i32 = g
    if gp(d) != 13
        return 7
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize("opt", ("-O0", "-O2"))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_huge_array_param_and_return_run_within_bound(ritz1_bin, tmp_path, compiler, opt):
    """The ticket's N = 65536: clang crashed at -O0 and hung at -O2."""
    ll = _ll(compiler, tmp_path, "huge", HUGE)
    # No first-class 64 KB value at all, even a dead one: a dead
    # `load [65536 x i8]` alone cost ritz0's IR 12 s at -O2.
    first_class = re.findall(r".*(?:load|store|ret|call) \[65536 x i8\].*", ll.read_text())
    assert not first_class, "\n".join(first_class[:5])
    obj = _object(ll, opt)
    # ritz0 emits its own _start for a `main`; ritz1 links the runtime's.
    assert _link_run([obj], tmp_path / f"huge{opt}", with_start=compiler == "ritz1") == 0


# --- IR shape ----------------------------------------------------------------

SHAPE = """\
pub fn take8(a: [300]u8) -> i32
    a[0] as i32

pub fn take32(a: [80]u32) -> u32
    a[0]

pub fn take64(a: [40]u64) -> u64
    a[0]

pub fn small(a: [4]u8) -> [4]u8
    a

pub fn make8(x: u8) -> [300]u8
    var b: [300]u8 = [x; 300]
    b

pub fn make32(x: u32) -> [80]u32
    [x; 80]

pub fn caller() -> i32
    var b: [300]u8 = make8(1)
    var c: [80]u32 = make32(2)
    var d: [40]u64 = [3; 40]
    let s = small([1; 4])
    take8(b) + take32(c) as i32 + take64(d) as i32 + s[0] as i32
"""

# {name: (element LLVM type, count, byval align)}
BYVAL = {
    "take8": ("i8", 300, 1),
    "take32": ("i32", 80, 4),
    "take64": ("i64", 40, 8),
}
SRET = {"make8": ("i8", 300), "make32": ("i32", 80)}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_array_params_are_byval_at_element_align(ritz1_bin, tmp_path, compiler):
    text = _ll(compiler, tmp_path, "shape", SHAPE).read_text()
    for fn, (et, n, align) in BYVAL.items():
        attr = rf"byval\(\[{n} x {et}\]\) align {align}\b"
        hdr = _header(text, "define", fn)
        assert re.search(attr, hdr), f"@{fn} is not byval align {align}:\n{hdr}"
        calls = _calls(text, fn)
        assert calls, f"no call to @{fn}"
        for line in calls:
            assert re.search(attr, line), f"call to @{fn} is not byval align {align}:\n{line}"
    assert not re.search(r"store \[(300|80|40) x i\d+\] %\"?a\.arg", text), (
        "a large array param is still spilled first-class"
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_array_returns_are_sret(ritz1_bin, tmp_path, compiler):
    text = _ll(compiler, tmp_path, "shape", SHAPE).read_text()
    for fn, (et, n) in SRET.items():
        attr = rf"sret\(\[{n} x {et}\]\)"
        hdr = _header(text, "define", fn)
        assert hdr.startswith("define") and " void @" in hdr and re.search(attr, hdr), (
            f"@{fn} does not return through sret([{n} x {et}]):\n{hdr}"
        )
        calls = _calls(text, fn)
        assert calls, f"no call to @{fn}"
        for line in calls:
            assert re.search(rf"call void @\"?{fn}\"?\(.*{attr}", line), (
                f"call to @{fn} is not sret:\n{line}"
            )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_small_array_param_and_return_are_unchanged(ritz1_bin, tmp_path, compiler):
    """A 4-byte array stays first-class: no ABI change below 256 bytes."""
    text = _ll(compiler, tmp_path, "shape", SHAPE).read_text()
    hdr = _header(text, "define", "small")
    assert "byval" not in hdr and "sret" not in hdr, hdr
    assert re.search(r"define [^@]*\[4 x i8\] @\"?small\"?\(\[4 x i8\] %", hdr), hdr


# --- the ABI is shared: each compiler calls the other's definitions ----------

LIB = """\
pub fn sum_ends(a: [1000]u32) -> u32
    a[0] = a[0] + 1000
    a[0] + a[999]

pub fn fill(x: u32) -> [1000]u32
    var b: [1000]u32 = [x; 1000]
    b[999] = x * 2
    b
"""

APP = """\
extern fn sum_ends(a: [1000]u32) -> u32
extern fn fill(x: u32) -> [1000]u32

fn main() -> i32
    var b: [1000]u32 = fill(7)
    if b[0] != 7 or b[999] != 14
        return 1
    if sum_ends(b) != 1021
        return 2
    if b[0] != 7
        return 3
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize("lib_c,app_c", (("ritz0", "ritz1"), ("ritz1", "ritz0")))
def test_large_array_abi_links_across_compilers(ritz1_bin, tmp_path, lib_c, app_c):
    lib = _object(_ll(lib_c, tmp_path, "lib", LIB), "-O0")
    app = _object(_ll(app_c, tmp_path, "app", APP), "-O0")
    assert _link_run([app, lib], tmp_path / "xlink", with_start=app_c == "ritz1") == 0
