"""AGAST #1847: attributes are a closed set; both compilers honour or reject.

ritz1 used to parse every bare `[[name]]` and drop it: a `[[packed]]` struct
got natural alignment and a `[[naked]]` fn got a prologue, with no error. A
ritz1-built kernel would lay out GDT/IDT/ACPI structures wrong in silence.

The rule (LANGUAGE_SPEC §17):

* the attributes are `test`, `test_helper` (AGAST #1869),
  `target_os = "..."`, `packed`, `naked`, `inline`, `always_inline`,
  `noinline` and `callconv = "..."`;
* anything else, or a known attribute on an item kind it does not apply to,
  is a compile error located at the attribute (file:line:col);
* `[[packed]]` structs have no padding: LLVM `<{ ... }>`, alignment 1, and
  sizeof / field offsets agree between ritz0 and ritz1;
* `[[naked]]` fns get LLVM `naked` and no prologue; their body may contain
  only `asm` blocks. ritz1 has no inline asm yet (AGAST #1619), so it rejects
  `[[naked]]` with a located error rather than emit something wrong.
* `[[inline]]` / `[[always_inline]]` / `[[noinline]]` reach each monomorph
  instance of a generic fn too (AGAST #1961); that test also runs on
  ritz1_selfhosted.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ1_SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

pytestmark = pytest.mark.integration


def _compile(compiler: str, tmp_path: Path, src: str, name: str = "t"):
    path = tmp_path / f"{name}.ritz"
    path.write_text(src)
    ll = tmp_path / f"{name}.ll"
    if ll.exists():
        ll.unlink()
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_SELFHOSTED_BIN if compiler == "ritz1_selfhosted" else RITZ1_BIN
        proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


def _ir(compiler: str, tmp_path: Path, src: str) -> str:
    proc, ll = _compile(compiler, tmp_path, src)
    assert proc.returncode == 0 and ll.exists(), (
        f"{compiler} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    return ll.read_text()


def _run(compiler: str, tmp_path: Path, src: str, opt: str = "-O0") -> int:
    _ir(compiler, tmp_path, src)
    ll = tmp_path / "t.ll"
    exe = tmp_path / f"t_{compiler}"
    link_cmd = ["clang", "-Wno-override-module", opt, str(ll), "-o", str(exe),
                "-nostdlib", "-no-pie"]
    if compiler in ("ritz1", "ritz1_selfhosted"):
        link_cmd.insert(1, str(RITZ_START))
    link = fast_link.clang(link_cmd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR did not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _assert_located_error(compiler, tmp_path, src, line, col, *needles):
    proc, ll = _compile(compiler, tmp_path, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted it:\n{out}"
    assert not ll.exists() or compiler == "ritz0", f"{compiler} still wrote {ll}"
    assert re.search(rf"t\.ritz:{line}:{col}\b", out), (
        f"{compiler}: error not located at t.ritz:{line}:{col}:\n{out}")
    for needle in needles:
        assert needle in out, f"{compiler}: {needle!r} not in:\n{out}"


COMPILERS = ["ritz0", "ritz1"]


def _need(compiler, request):
    if compiler == "ritz1":
        request.getfixturevalue("ritz1_bin")
    elif compiler == "ritz1_selfhosted":
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert RITZ1_SELFHOSTED_BIN.exists(), (
            f"{RITZ1_SELFHOSTED_BIN} missing; run `make -C ritz1 bootstrap`")


# --- unknown / misplaced attributes -----------------------------------------

UNKNOWN_BARE = """\
fn helper() -> i32
    1

[[frobnicate]]
fn main() -> i32
    helper()
"""

UNKNOWN_KV = """\
[[target_arch = "x86_64"]]
fn main() -> i32
    0
"""

PACKED_ON_FN = """\
[[packed]]
fn main() -> i32
    0
"""

NAKED_ON_STRUCT = """\
[[naked]]
struct S
    a: u8

fn main() -> i32
    0
"""

TEST_ON_STRUCT = """\
[[test]]
struct S
    a: u8

fn main() -> i32
    0
"""

TARGET_OS_BARE = """\
[[target_os]]
fn main() -> i32
    0
"""

TEST_HELPER_ON_STRUCT = """\
[[test_helper]]
struct S
    a: u8

fn main() -> i32
    0
"""

TEST_HELPER_WITH_VALUE = """\
[[test_helper = "yes"]]
fn h()
    assert 1 == 1

fn main() -> i32
    0
"""

PACKED_WITH_VALUE = """\
[[packed = "yes"]]
struct S
    a: u8

fn main() -> i32
    0
"""

UNKNOWN_IN_LIST = """\
[[test, frobnicate]]
fn main() -> i32
    0
"""

ERRORS = {
    # name: (source, line, col, needles)
    "unknown_bare": (UNKNOWN_BARE, 4, 3, ["unknown attribute", "frobnicate"]),
    "unknown_kv": (UNKNOWN_KV, 1, 3, ["unknown attribute", "target_arch"]),
    "packed_on_fn": (PACKED_ON_FN, 1, 3, ["packed", "struct"]),
    "naked_on_struct": (NAKED_ON_STRUCT, 1, 3, ["naked", "fn"]),
    "test_on_struct": (TEST_ON_STRUCT, 1, 3, ["test", "fn"]),
    "target_os_bare": (TARGET_OS_BARE, 1, 3, ["target_os", "value"]),
    "packed_with_value": (PACKED_WITH_VALUE, 1, 3, ["packed", "value"]),
    "test_helper_on_struct": (TEST_HELPER_ON_STRUCT, 1, 3, ["test_helper", "fn"]),
    "test_helper_with_value": (TEST_HELPER_WITH_VALUE, 1, 3, ["test_helper", "value"]),
    # Each name in a comma list is judged, and located, on its own (#1919).
    "unknown_in_list": (UNKNOWN_IN_LIST, 1, 9, ["unknown attribute", "frobnicate"]),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(ERRORS))
def test_bad_attribute_is_a_located_error(request, tmp_path, compiler, case):
    _need(compiler, request)
    src, line, col, needles = ERRORS[case]
    _assert_located_error(compiler, tmp_path, src, line, col, *needles)


# The set every compiler-built source in the repo uses must keep compiling.
KNOWN_OK = """\
[[target_os = "linux"]]
fn which() -> i32
    1

[[target_os = "harland"]]
fn which() -> i32
    2

[[test]]
fn test_it() -> i32
    0

[[test_helper]]
fn helper_it(x: i64)
    assert x == x

[[inline]]
fn a() -> i32
    1

[[always_inline]]
fn b() -> i32
    2

[[noinline]]
fn c() -> i32
    3

fn main() -> i32
    which() + a() + b() + c()
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_known_attributes_compile(request, tmp_path, compiler):
    _need(compiler, request)
    assert _run(compiler, tmp_path, KNOWN_OK) == 7


# `[[a, b]]` is `[[a]] [[b]]` (LANGUAGE_SPEC §17, AGAST #1919): every entry
# applies: dropping packed makes sizeof(P) 16, dropping target_os leaves two
# which()s.  A trailing comma is accepted, as ritz0 accepts it.  The gated twin
# is a fn, not a struct: ritz0 rejects same-named gated structs (#4054).
ATTR_LIST = """\
[[packed, target_os = "linux"]]
struct P
    a: u8
    b: u64

[[inline, target_os = "linux",]]
fn which() -> i32
    1

[[target_os = "harland", inline]]
fn which() -> i32
    2

fn main() -> i32
    if sizeof(P) != 9
        return 1
    which() + 41
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_comma_separated_attribute_list(request, tmp_path, compiler):
    _need(compiler, request)
    assert _run(compiler, tmp_path, ATTR_LIST) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
def test_inline_family_reaches_the_ir(request, tmp_path, compiler):
    _need(compiler, request)
    ir = _ir(compiler, tmp_path, KNOWN_OK)
    defs = {m.group(1): m.group(0) for m in
            re.finditer(r'^define [^@]*@"?(\w+)"?\(.*$', ir, re.M)}

    def attrs_of(fn):
        line = defs[fn]
        # llvmlite puts fn attributes in an attribute group (#N).
        groups = re.findall(r"#(\d+)", line)
        text = line
        for g in groups:
            m = re.search(rf"^attributes #{g} = \{{(.*)\}}", ir, re.M)
            text += " " + (m.group(1) if m else "")
        return text

    assert re.search(r"\binlinehint\b", attrs_of("a")), defs["a"]
    assert re.search(r"\balwaysinline\b", attrs_of("b")), defs["b"]
    assert re.search(r"\bnoinline\b", attrs_of("c")), defs["c"]
    assert not re.search(r"inline", attrs_of("main")), defs["main"]


# AGAST #1961: a generic fn's inline-family attribute reaches each of its
# monomorph instances (`hint$i32` ...), not only non-generic fns.  ritz1 once
# copied [[callconv]] / [[test_helper]] / [[must_use]] to an instance but not
# these, so every instance came out with no inline attribute at all.
GENERIC_INLINE = """\
[[inline]]
fn hint<T>(x: T) -> T
    x

[[always_inline]]
fn always<T>(x: T) -> T
    x

[[noinline]]
fn never<T>(x: T) -> T
    x

fn plain<T>(x: T) -> T
    x

fn main() -> i32
    hint(1) + always(2) + never(3) + plain(4)
"""


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
def test_inline_family_reaches_generic_instances(request, tmp_path, compiler):
    _need(compiler, request)
    ir = _ir(compiler, tmp_path, GENERIC_INLINE)

    def attrs_of(base):
        # The instance's mangled name varies by compiler; it starts with `base`
        # and is the only define that does.
        lines = [m.group(0) for m in re.finditer(
            rf'^define [^@]*@"?{base}\b[^(]*\(.*$', ir, re.M)]
        assert len(lines) == 1, f"{compiler}: instances of {base}: {lines}"
        text = lines[0]
        for g in re.findall(r"#(\d+)", lines[0]):
            m = re.search(rf"^attributes #{g} = \{{(.*)\}}", ir, re.M)
            text += " " + (m.group(1) if m else "")
        return text

    assert re.search(r"\binlinehint\b", attrs_of("hint")), attrs_of("hint")
    assert re.search(r"\balwaysinline\b", attrs_of("always")), attrs_of("always")
    assert re.search(r"\bnoinline\b", attrs_of("never")), attrs_of("never")
    assert not re.search(r"inline", attrs_of("plain")), attrs_of("plain")


# --- [[packed]] --------------------------------------------------------------

PACKED = """\
[[packed]]
struct P
    a: u8
    b: u64
    c: u16
    d: u8

struct Normal
    a: u8
    b: u64
    c: u16
    d: u8

# A packed struct is 1-aligned, so it sits at offset 1 here, not 8.
struct Outer
    x: u8
    p: P
    y: u8

fn off(base: *u8, field: *u8) -> i64
    field as i64 - base as i64

fn main() -> i32
    var p: P
    var o: Outer
    p.a = 0x11
    p.b = 0x2222222222222222
    p.c = 0x3333
    p.d = 0x44
    if p.a != 0x11 or p.b != 0x2222222222222222 or p.c != 0x3333 or p.d != 0x44
        return 1
    if sizeof(P) != 12
        return 2
    if sizeof(Normal) != 24
        return 3
    if off(@p as *u8, @p.b as *u8) != 1 or off(@p as *u8, @p.c as *u8) != 9 or off(@p as *u8, @p.d as *u8) != 11
        return 4
    if sizeof(Outer) != 14
        return 5
    if off(@o as *u8, @o.p as *u8) != 1 or off(@o as *u8, @o.y as *u8) != 13
        return 6
    o.p.b = 7
    if o.p.b != 7
        return 7
    42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_packed_layout_runs(request, tmp_path, compiler):
    _need(compiler, request)
    assert _run(compiler, tmp_path, PACKED) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
def test_packed_struct_type_is_llvm_packed(request, tmp_path, compiler):
    _need(compiler, request)
    ir = _ir(compiler, tmp_path, PACKED)
    norm = lambda s: re.sub(r"\s+", "", s)
    # ritz0 names types `%"struct.<module>.P"`, ritz1 `%P`.
    types = {m.group(1).rsplit(".", 1)[-1]: norm(m.group(2)) for m in
             re.finditer(r'^%"?([\w.$]+)"?\s*=\s*type\s*(.*)$', ir, re.M)}
    assert types["P"] == "<{i8,i64,i16,i8}>", types
    assert types["Normal"] == "{i8,i64,i16,i8}", types
    assert types["Outer"].startswith("{"), types


@pytest.mark.parametrize("compiler", COMPILERS)
def test_packed_layout_runs_at_O2(request, tmp_path, compiler):
    _need(compiler, request)
    assert _run(compiler, tmp_path, PACKED, opt="-O2") == 42


# --- AGAST #1918: packed-field accesses carry `align 1` ----------------------
#
# A field of a `[[packed]]` struct can sit at any offset, so `load i64` from
# `p.b` (offset 1) with no `align` operand claims ABI alignment 8 — UB that
# -O2 is entitled to exploit.  Every shape below reaches a field of a packed
# struct: directly, through a pointer, through an array element, nested
# inside a normal struct, and a normal struct nested inside a packed one.

PACKED_ACCESS = """\
struct Inner
    x: u32
    y: u64

[[packed]]
struct P
    a: u8
    b: u64
    c: u16
    inner: Inner

struct Outer
    x: u8
    p: P

var g: P

fn via_ptr(q: *P) -> u64
    q.b = q.b + 1
    q.b

fn main() -> i32
    var p: P
    var o: Outer
    var arr: [2]P
    p.b = 5
    p.c = 6
    p.b += 1
    o.p.b = 7
    o.p.inner.y = 8
    p.inner.x = 9
    arr[1].b = 10
    g.b = 11
    let r: u64 = p.b + p.c as u64 + o.p.b + o.p.inner.y + p.inner.x as u64 + arr[1].b + g.b + via_ptr(@p)
    if r != 6 + 6 + 7 + 8 + 9 + 10 + 11 + 7
        return 1
    42
"""

_REG = r'(?:%"[^"]+"|%[\w.$-]+)'


def _struct_name(tok: str) -> str:
    # ritz0: `%"struct.<module>.P"`, ritz1: `%P`.
    return tok.strip('%"').rsplit(".", 1)[-1]


def _packed_accesses(ir: str, names=frozenset({"P"})):
    """(line, has_align1) for each load/store through a field of `names`.

    A pointer is derived when a GEP's source type is one of `names`,
    or its base is itself packed-derived (nesting).  The GEP's result is the
    register defined; the base is the first register operand after the
    source type (skipping ritz0's typed-pointer `%T*` spelling).
    """
    packed = set()
    out = []
    for line in ir.splitlines():
        code = line.split(", !dbg")[0]
        m = re.match(rf"\s*({_REG}) = getelementptr (?:inbounds )?(.*)$", code)
        if m:
            dst, rest = m.group(1), m.group(2)
            src_ty = re.match(rf"({_REG}|\[[^\]]*\]|\w+)", rest).group(1)
            after = rest[len(src_ty):]
            base = None
            for bm in re.finditer(_REG, after):
                if after[bm.end():bm.end() + 1] == "*":
                    continue   # ritz0's `%"struct.P"*` pointer type
                base = bm.group(0)
                break
            if (src_ty.startswith("%") and _struct_name(src_ty) in names) or base in packed:
                packed.add(dst)
            continue
        m = re.match(rf"\s*(?:{_REG} = load .*|store .*), (?:ptr|\S+\*) ({_REG})(.*)$", code)
        if m and m.group(1) in packed:
            out.append((line.strip(), re.search(r",\s*align 1\b", m.group(2)) is not None))
    return out


@pytest.mark.parametrize("compiler", COMPILERS)
def test_packed_field_accesses_are_align_1(request, tmp_path, compiler):
    _need(compiler, request)
    ir = _ir(compiler, tmp_path, PACKED_ACCESS)
    accesses = _packed_accesses(ir)
    # One store and one load per shape at least — the check must not be vacuous.
    assert len(accesses) >= 16, "\n".join(a for a, _ in accesses) or ir
    bad = [a for a, ok in accesses if not ok]
    assert not bad, "packed-field access without `align 1`:\n" + "\n".join(bad)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_packed_field_accesses_run_at_O2(request, tmp_path, compiler):
    _need(compiler, request)
    assert _run(compiler, tmp_path, PACKED_ACCESS, opt="-O2") == 42


# A packed struct in the module too, so ritz1's pass actually runs.
NORMAL_ONLY = """\
struct N
    a: u8
    b: u64

[[packed]]
struct Q
    a: u8
    b: u64

fn main() -> i32
    var n: N
    var q: Q
    n.b = 40
    q.b = 2
    (n.b + q.b) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_normal_struct_accesses_keep_natural_alignment(request, tmp_path, compiler):
    # The fix must not degrade every field access to `align 1`.
    _need(compiler, request)
    ir = _ir(compiler, tmp_path, NORMAL_ONLY)
    normal = _packed_accesses(ir, frozenset({"N"}))
    assert len(normal) >= 2, ir
    assert not any(ok for _, ok in normal), "\n".join(a for a, _ in normal)
    assert all(ok for _, ok in _packed_accesses(ir, frozenset({"Q"}))), ir


GENERIC_PACKED = """\
[[packed]]
struct Pair<T>
    tag: u8
    val: T

# The array stride and sizeof (which parses since AGAST #3268) agree.
fn main() -> i32
    var arr: [2]Pair<u64>
    arr[1].tag = 1
    arr[1].val = 41
    if @arr[1] as i64 - @arr[0] as i64 != 9
        return 1
    if sizeof(Pair<u64>) != 9
        return 2
    (arr[1].tag as u64 + arr[1].val) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_packed_survives_monomorphisation(request, tmp_path, compiler):
    _need(compiler, request)
    assert _run(compiler, tmp_path, GENERIC_PACKED) == 42


# --- [[naked]] ---------------------------------------------------------------

NAKED = """\
[[naked]]
fn naked_add(a: i32, b: i32) -> i32
    asm x86_64:
        movl %edi, %eax
        addl %esi, %eax
        retq

fn main() -> i32
    naked_add(40, 2)
"""


def test_ritz0_naked_has_no_prologue(tmp_path):
    ir = _ir("ritz0", tmp_path, NAKED)
    m = re.search(r'^define [^\n]*@"?naked_add"?\(.*?^}', ir, re.M | re.S)
    assert m, ir
    body = m.group(0)
    header = body.splitlines()[0]
    groups = re.findall(r"#(\d+)", header)
    attrs = header + " ".join(
        (re.search(rf"^attributes #{g} = \{{(.*)\}}", ir, re.M) or [None, ""])[1]
        for g in groups)
    assert re.search(r"\bnaked\b", attrs), header
    # No prologue: parameters are not spilled to stack slots.
    assert "alloca" not in body and "store" not in body, body
    assert "unreachable" in body, body


def test_ritz0_naked_runs(tmp_path):
    assert _run("ritz0", tmp_path, NAKED) == 42


def test_ritz0_naked_runs_at_O2(tmp_path):
    # AGAST #1917: a naked fn's IR body is asm + `unreachable` (the asm does
    # its own `ret`). Inlined at -O2, that `ret` returned from the *caller*
    # and everything after the call was deleted as unreachable: SIGSEGV.
    # Shipped programs are -O2, so a naked fn must never be inlined.
    assert _run("ritz0", tmp_path, NAKED, "-O2") == 42


def test_ritz0_naked_is_noinline(tmp_path):
    ir = _ir("ritz0", tmp_path, NAKED)
    header = re.search(r'^define [^\n]*@"?naked_add"?\(.*$', ir, re.M).group(0)
    assert re.search(r"\bnoinline\b", header), header


NAKED_NON_ASM = """\
[[naked]]
fn bad() -> i32
    let x: i32 = 1
    x

fn main() -> i32
    0
"""


def test_ritz0_naked_body_must_be_asm(tmp_path):
    # ritz0 used to skip every non-asm statement in a naked fn in silence.
    _assert_located_error("ritz0", tmp_path, NAKED_NON_ASM, 3, 5, "naked", "asm")


NAKED_RITZ1 = """\
[[naked]]
fn bare() -> i32
    0

fn main() -> i32
    0
"""


def test_ritz1_naked_body_must_be_asm(ritz1_bin, tmp_path):
    # ritz1 parses asm (AGAST #3394), so `[[naked]]` is judged as ritz0 judges
    # it: at the statement that isn't asm.
    _assert_located_error("ritz1", tmp_path, NAKED_RITZ1, 3, 5, "naked", "only asm")


def test_ritz1_naked_has_no_prologue_and_runs_at_O2(ritz1_bin, tmp_path):
    # AGAST #3395: ritz1 lowers asm, so a naked fn is emitted as ritz0 emits
    # it: `naked noinline` (#1917), no slot for a parameter, the blocks, then
    # `unreachable`.
    ir = _ir("ritz1", tmp_path, NAKED)
    m = re.search(r'^define [^\n]*@"?naked_add"?\(.*?^}', ir, re.M | re.S)
    assert m, ir
    body = m.group(0)
    header = body.splitlines()[0]
    assert re.search(r"\bnaked\b", header) and re.search(r"\bnoinline\b", header), header
    assert "alloca" not in body and "store" not in body, body
    assert "unreachable" in body, body
    assert _run("ritz1", tmp_path, NAKED, "-O2") == 42


# AGAST #3633: a generic `[[naked]]` fn's instances are naked too (§17.5).
# ritz1's fn_copy_instance_attrs copied only callconv / test_helper / must_use
# and the inline family (#1961), so `nk$i64` was checked and emitted as an
# ordinary fn: "can reach its end without producing a value".
GENERIC_NAKED = """\
[[naked]]
fn nk<T>(a: T) -> T
    asm x86_64:
        movq %rdi, %rax
        retq

fn main() -> i32
    nk(42) as i32
"""


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
def test_naked_reaches_generic_instances(request, tmp_path, compiler):
    _need(compiler, request)
    ir = _ir(compiler, tmp_path, GENERIC_NAKED)
    defs = re.findall(r'^define [^\n]*@"?nk\b[^\n]*\n.*?^}', ir, re.M | re.S)
    assert len(defs) == 1, f"{compiler}: instances of nk: {defs}"
    body = defs[0]
    header = body.splitlines()[0]
    attrs = header + " ".join(
        (re.search(rf"^attributes #{g} = \{{(.*)\}}", ir, re.M) or [None, ""])[1]
        for g in re.findall(r"#(\d+)", header))
    assert re.search(r"\bnaked\b", attrs) and re.search(r"\bnoinline\b", attrs), header
    assert "alloca" not in body and "store" not in body, body
    assert "unreachable" in body, body
    # Inlined at -O2, the asm's own `ret` would return from main (#1917).
    assert _run(compiler, tmp_path, GENERIC_NAKED, "-O2") == 42


GENERIC_NAKED_NON_ASM = """\
[[naked]]
fn nk<T>(a: T) -> T
    a

fn main() -> i32
    nk(1) as i32
"""


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
def test_generic_naked_body_must_be_asm(request, tmp_path, compiler):
    # The instance is judged as a naked fn, at the template's statement.
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, GENERIC_NAKED_NON_ASM, 3, 5, "naked", "asm")
