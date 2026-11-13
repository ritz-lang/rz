"""AGAST #1880: explicit enum discriminants, integer conversion, const patterns.

LANGUAGE_SPEC §10.4 and §8.2 specify them; this pins each one on ritz0, ritz1
and ritz1_selfhosted, as behaviour (a linked program's exit code) and as
located rejections:

* `enum E: T` gives a fieldless enum a representation type T (an integer
  type); `Variant = N` gives a variant discriminant N, and a variant without
  one takes the previous discriminant + 1 (the first takes 0).
* `e as U` converts a fieldless enum value to any integer type U: its
  discriminant (its declaration index when the enum has no representation
  type).
* `E.from(v)` converts a T back: `Some(variant)` whose discriminant is v, or
  `None`.  It exists for an enum with a representation type, declared in a
  module that imports ritzlib.option.
* A bare identifier pattern naming an integer `const` compares against the
  constant (`SYS_READ =>`) instead of binding a new name.

Every program here returns a code that names the first check it failed, so a
compiler that gets one conversion wrong fails with a number that says which.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
SPEC = RITZ_ROOT / "docs" / "LANGUAGE_SPEC.md"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration


def _compile(compiler, tmp_path, src, name="t", extra=()):
    path = tmp_path / f"{name}.ritz"
    path.write_text(src)
    ll = tmp_path / f"{name}_{compiler}.ll"
    if ll.exists():
        ll.unlink()
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path,
                         env=env, timeout=300), ll
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


def _ir(compiler, tmp_path, src, name="t", extra=()):
    proc, ll = _compile(compiler, tmp_path, src, name, extra)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {name}:\n{out}"
    return ll


def _run(compiler, tmp_path, src, modules=None):
    """Compile `src` (and each helper module), link, run; return the exit code.

    `modules` maps a module name to its source.  Each is compiled to its own
    object, as a build does: an importer only declares the imported fns.
    """
    objs = []
    for mod_name, mod_src in (modules or {}).items():
        # ritz0 emits a _start unless told not to; only the main object may.
        extra = ("--no-runtime",) if compiler == "ritz0" else ()
        objs.append(str(_ir(compiler, tmp_path, mod_src, mod_name, extra)))
    objs.insert(0, str(_ir(compiler, tmp_path, src)))
    if compiler != "ritz0":
        objs.insert(0, str(RITZ_START))
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _rejected(compiler, tmp_path, src, needle, where):
    proc, _ = _compile(compiler, tmp_path, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted:\n{src}\n{out}"
    assert needle in out, f"{compiler}: rejected, but not with {needle!r}:\n{out}"
    assert re.search(rf"{re.escape(where)}\b", out), (
        f"{compiler}: error not located at {where}:\n{out}")


# --- discriminants and `as` --------------------------------------------------

AS_INT = """\
enum Sys: u64
    Read = 0
    Write
    Mmap = 9
    Exit = 60
    Big = 0xFFFFFFFF00

enum Errno: i64
    Success
    Fault = -14
    Inval = -22
    Next

enum Plain
    A
    B
    C

struct Holder
    s: Sys
    n: i32

fn code(s: Sys) -> u64
    s as u64

fn main() -> i32
    if Sys.Read as u64 != 0
        return 1
    if Sys.Write as u64 != 1
        return 2
    if Sys.Mmap as u64 != 9
        return 3
    let e = Sys.Exit
    if e as u64 != 60
        return 4
    if Sys.Big as u64 != 0xFFFFFFFF00
        return 5
    if Errno.Fault as i64 != -14
        return 6
    if Errno.Next as i64 != -21
        return 7
    if Errno.Success as i64 != 0
        return 8
    if Plain.C as i32 != 2
        return 9
    # A narrowing conversion truncates the discriminant, as for an integer.
    if Sys.Big as u8 != 0
        return 10
    if code(Sys.Mmap) != 9
        return 11
    let h = Holder { s: Sys.Exit, n: 1 }
    if h.s as u64 != 60
        return 12
    var v: Errno = Errno.Inval
    let w: i32 = v as i32
    if w != -22
        return 13
    # Matching still goes by variant.
    match e
        Exit => 42
        _ => 14
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_as_integer(compiler, tmp_path):
    assert _run(compiler, tmp_path, AS_INT) == 42


# --- E.from ------------------------------------------------------------------

FROM = """\
import ritzlib.option

enum Sys: u64
    Read = 0
    Write
    Mmap = 9
    Exit = 60

enum Errno: i32
    Fault = -14
    Inval = -22

fn which(n: u64) -> i32
    match Sys.from(n)
        Some(s) => match s
            Read => 1
            Write => 2
            Mmap => 3
            Exit => 4
        None => 0

fn round_trip(n: u64) -> u64
    match Sys.from(n)
        Some(s) => s as u64
        None => 999

fn errno_ok(n: i32) -> i32
    let o = Errno.from(n)
    match o
        Some(_) => 1
        None => 0

fn main() -> i32
    if which(0) != 1
        return 1
    if which(1) != 2
        return 2
    if which(9) != 3
        return 3
    if which(60) != 4
        return 4
    if which(2) != 0
        return 5
    if which(61) != 0
        return 6
    if round_trip(60) != 60
        return 7
    if round_trip(8) != 999
        return 8
    if errno_ok(-14) != 1
        return 9
    if errno_ok(-15) != 0
        return 10
    if errno_ok(14) != 0
        return 11
    42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_from(compiler, tmp_path):
    assert _run(compiler, tmp_path, FROM) == 42


# `E.from` inside a generic fn: its body reaches emission only as a
# specialisation (ritz1 rewrites the call where monomorph clones it).
FROM_GENERIC = """\
import ritzlib.option

enum Sys: u64
    Read = 0
    Exit = 60

fn code<T>(x: T, n: u64) -> i32
    match Sys.from(n)
        Some(s) => match s
            Exit => 4
            _ => 5
        None => 6

fn main() -> i32
    code<i32>(1, 60) * 10 + code<i32>(1, 3)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_from_in_generic_fn(compiler, tmp_path):
    assert _run(compiler, tmp_path, FROM_GENERIC) == 46


# --- const patterns ------------------------------------------------------------

CONST_PATTERNS = """\
const K_READ: u64 = 0
const K_WRITE: u64 = 1
const NEG: i64 = -5

fn classify(n: u64) -> i32
    match n
        K_READ => 10
        K_WRITE => 20
        K_EXIT => 30
        other => other as i32

# Declared after its use: a const pattern resolves module-wide.
const K_EXIT: u64 = 60

fn neg(n: i64) -> i32
    match n
        NEG => 1
        _ => 2

fn stmt_form(n: u64) -> i32
    var r: i32 = 0
    match n
        K_EXIT => r = 7
        _ => r = 8
    r

fn main() -> i32
    if classify(0) != 10
        return 1
    if classify(1) != 20
        return 2
    if classify(60) != 30
        return 3
    # A name that is no const still binds.
    if classify(5) != 5
        return 4
    if neg(-5) != 1
        return 5
    if neg(5) != 2
        return 6
    if stmt_form(60) != 7
        return 7
    if stmt_form(1) != 8
        return 8
    42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_const_patterns(compiler, tmp_path):
    assert _run(compiler, tmp_path, CONST_PATTERNS) == 42


# --- across modules ------------------------------------------------------------

NUMBERS = """\
import ritzlib.option

pub const SYS_READ: u64 = 0
pub const SYS_EXIT: u64 = 60

pub enum Sys: u64
    Read = 0
    Write
    Exit = 60
"""

CROSS = """\
import ritzlib.option
import numbers

fn dispatch(n: u64) -> i32
    match n
        SYS_READ => 1
        SYS_EXIT => 2
        _ => 3

fn decode(n: u64) -> i32
    match Sys.from(n)
        Some(s) => match s
            Exit => 4
            _ => 5
        None => 6

fn main() -> i32
    if dispatch(0) != 1
        return 1
    if dispatch(60) != 2
        return 2
    if dispatch(1) != 3
        return 3
    if decode(60) != 4
        return 4
    if decode(1) != 5
        return 5
    if decode(7) != 6
        return 6
    if Sys.Exit as u64 != SYS_EXIT
        return 7
    42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_across_modules(compiler, tmp_path):
    assert _run(compiler, tmp_path, CROSS, {"numbers": NUMBERS}) == 42


# --- rejections ----------------------------------------------------------------

REJECTS = {
    "discriminant_needs_repr": ("""\
enum E
    A
    B = 3

fn main() -> i32
    0
""", "discriminant of variant 'B' needs a representation type: write 'enum E: <integer type>'",
        "t.ritz:3"),
    "repr_not_integer": ("""\
enum E: f64
    A

fn main() -> i32
    0
""", "representation type of enum 'E' must be an integer type", "t.ritz:1"),
    "repr_with_payload": ("""\
enum E: u8
    A
    B(i32)

fn main() -> i32
    0
""", "variant 'B' of enum 'E' carries data, so the enum cannot have a representation type",
        "t.ritz:3"),
    "duplicate": ("""\
enum E: u8
    A = 3
    B = 2
    C

fn main() -> i32
    0
""", "variants 'A' and 'C' of enum 'E' have the same discriminant 3", "t.ritz:4"),
    "out_of_range": ("""\
enum E: u8
    A = 256

fn main() -> i32
    0
""", "discriminant 256 of variant 'A' does not fit enum 'E''s representation type u8",
        "t.ritz:2"),
    "negative_unsigned": ("""\
enum E: u32
    A = -1

fn main() -> i32
    0
""", "discriminant -1 of variant 'A' does not fit enum 'E''s representation type u32",
        "t.ritz:2"),
    "implicit_overflow": ("""\
enum E: i8
    A = 127
    B

fn main() -> i32
    0
""", "discriminant 128 of variant 'B' does not fit enum 'E''s representation type i8",
        "t.ritz:3"),
    "cast_payload_enum": ("""\
enum Shape
    Circle(i64)
    Empty

fn main() -> i32
    let s = Shape.Empty
    s as i32
""", "cannot convert enum 'Shape' to an integer: variant 'Circle' carries data", "t.ritz:7"),
    "from_without_repr": ("""\
import ritzlib.option

enum Plain
    A
    B

fn main() -> i32
    match Plain.from(1)
        Some(_) => 1
        None => 0
""", "enum 'Plain' has no 'from'", "t.ritz:8"),
    "from_without_option": ("""\
enum E: u8
    A

fn main() -> i32
    let o = E.from(0)
    0
""", "enum 'E' has no 'from'", "t.ritz:5"),
}

# AGAST #2136: §10.4 "Convert explicitly to pass one as an integer." An enum
# value where an integer is expected is a located error at each place a value
# meets a declared type: return (statement and tail), argument, annotated
# let / var, and assignment.  ritz0 used to emit `ret %enum.St` from an i64
# fn (invalid IR) and ritz1 accepted all of them.
_ST = """\
enum St
    A
    B

enum Errno: i64
    Fault = -14

struct Box
    n: i64

fn take(x: u64) -> i64
    x as i64

"""
_AS_INT = "found enum '{}'; convert with `as`"
REJECTS.update({
    "enum_as_int_return": (_ST + """\
fn f() -> i64
    return St.B

fn main() -> i32
    f() as i32
""", "expected i64, " + _AS_INT.format("St"), "t.ritz:15"),
    "enum_as_int_tail": (_ST + """\
fn f() -> i64
    Errno.Fault

fn main() -> i32
    f() as i32
""", "expected i64, " + _AS_INT.format("Errno"), "t.ritz:15"),
    "enum_as_int_argument": (_ST + """\
fn main() -> i32
    take(St.A) as i32
""", "expected u64, " + _AS_INT.format("St"), "t.ritz:15"),
    "enum_as_int_let": (_ST + """\
fn main() -> i32
    let n: i32 = St.B
    n
""", "expected i32, " + _AS_INT.format("St"), "t.ritz:15"),
    "enum_as_int_var": (_ST + """\
fn main() -> i32
    var n: i64 = Errno.Fault
    n as i32
""", "expected i64, " + _AS_INT.format("Errno"), "t.ritz:15"),
    "enum_as_int_assign": (_ST + """\
fn main() -> i32
    var n: i64 = 0
    n = St.B
    n as i32
""", "expected i64, " + _AS_INT.format("St"), "t.ritz:16"),
    "enum_as_int_assign_field": (_ST + """\
fn main() -> i32
    var b = Box { n: 0 }
    b.n = St.B
    b.n as i32
""", "expected i64, " + _AS_INT.format("St"), "t.ritz:16"),
    # The expression forms: `return` and assignment as a match arm.
    "enum_as_int_return_arm": (_ST + """\
fn f(k: i64) -> i64
    match k
        0 => return St.B
        _ => 1

fn main() -> i32
    f(0) as i32
""", "expected i64, " + _AS_INT.format("St"), "t.ritz:16"),
    "enum_as_int_assign_arm": (_ST + """\
fn main() -> i32
    var n: i64 = 0
    match n
        0 => n = Errno.Fault
        _ => pass
    n as i32
""", "expected i64, " + _AS_INT.format("Errno"), "t.ritz:17"),
})

# The controls: an enum where an enum is expected, an explicit `as`, and an
# enum-valued tail in a procedure (whose tail is evaluated for effect) all
# still compile and run.
ENUM_POSITIONS_OK = _ST + """\
fn pick(s: St) -> St
    s

fn st() -> St
    return St.B

fn proc()
    St.A

fn main() -> i32
    proc()
    var s: St = St.A
    s = pick(st())
    let n: i64 = s as i64
    var b = Box { n: 0 }
    b.n = Errno.Fault as i64
    if n != 1
        return 1
    if b.n != -14
        return 2
    take(St.B as u64) as i32 + 40
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_enum_positions_ok(compiler, tmp_path):
    assert _run(compiler, tmp_path, ENUM_POSITIONS_OK) == 41


# AGAST #2135: `d as *Hdr` of a pointer param, in a fn with a local of a
# struct that has an enum field.  ritz1 resolved `d` as an enum and lowered
# the cast as enum → int: `extractvalue %St` on the i64 pointer, which clang
# rejects.
PTR_CAST_BESIDE_ENUM_FIELD = """\
struct Hdr
    a: u64

enum St: u8
    Ok
    Bad = 5

struct Res
    s: St
    v: u64

fn first(d: *u8) -> u64
    var r: Res
    r.s = St.Bad
    let h: *Hdr = d as *Hdr
    (*h).a + r.s as u64

fn main() -> i32
    var x: Hdr
    x.a = 37
    first(@x as *u8) as i32      # 42
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_ptr_cast_beside_enum_field(compiler, tmp_path):
    assert _run(compiler, tmp_path, PTR_CAST_BESIDE_ENUM_FIELD) == 42


# The control for #2135's fix: a `*St` local is no enum, but `*p` is one --
# matched, and converted with `as`.
DEREF_ENUM_PTR = """\
enum St: u8
    Ok
    Bad = 5

fn pick(p: *St) -> i32
    match *p
        Ok => 1
        Bad => 2

fn disc(p: *St) -> u64
    (*p) as u64

fn main() -> i32
    var s: St = St.Bad
    var q: *St = @s
    let a: i32 = pick(@s)
    let b: u64 = disc(@s)
    let c: u64 = (*q) as u64
    a + (b as i32) * 10 + (c as i32) - 15   # 2 + 50 + 5 - 15
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_deref_enum_ptr(compiler, tmp_path):
    assert _run(compiler, tmp_path, DEREF_ENUM_PTR) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(REJECTS))
def test_rejected(compiler, case, tmp_path):
    src, needle, where = REJECTS[case]
    _rejected(compiler, tmp_path, src, needle, where)


# --- the spec's own examples, on every compiler ----------------------------------

def _spec_examples():
    """The compiling ```ritz blocks of LANGUAGE_SPEC §10.4 and of §8.2's
    constant-pattern subsection: the doc gate compiles them with ritz0 only."""
    text = SPEC.read_text()
    blocks = []
    for start, end in (("### 10.4 ", "\n---\n"), ("#### Constant Patterns", "\n#### ")):
        i = text.index(start)
        section = text[i:text.index(end, i + len(start))]
        blocks += re.findall(r"```ritz\n(.*?)```", section, re.S)
    assert len(blocks) >= 3, "the spec sections lost their examples"
    return blocks


@pytest.mark.parametrize("compiler", COMPILERS)
def test_spec_examples(compiler, tmp_path):
    for i, block in enumerate(_spec_examples()):
        _ir(compiler, tmp_path, block, name=f"spec{i}")


# --- the generated `from` in ritz0's module interfaces (no compiler run) ---------

GEN_SRC = """\
import ritzlib.option

pub enum Sys: u64
    Read = 0
    Exit = 60

fn f() -> i32
    0
"""


@pytest.mark.unit
def test_interface_text_regenerates_from():
    """The interface text keeps the enum and drops nothing it lacks: the
    generated fn has no source lines, so it must not be stripped (that raised
    KeyError) and parsing the text must generate it again."""
    import module_interface as mi
    tokens, module = mi._parse_with_tokens(GEN_SRC, "gen.ritz")
    gen = [it for it in module.items if getattr(it, "generated", False)]
    assert [g.name for g in gen] == ["Sys__from"]
    assert gen[0].is_pub and gen[0].span.line == 3, "starts on the enum's line"
    text = mi.interface_text(GEN_SRC, tokens, module)
    assert "__from" not in text
    reparsed = mi.parse_source(text, "gen.ritz")
    assert any(isinstance(it, type(gen[0])) and it.name == "Sys__from"
               for it in reparsed.items)


@pytest.mark.unit
def test_metadata_keeps_discriminants():
    """The .ritz-meta path carries explicit discriminants to an importer."""
    import module_interface as mi
    from metadata import extract_metadata, metadata_from_json, metadata_to_json
    from import_resolver import ImportResolver
    module = mi.parse_source(GEN_SRC, "gen.ritz")
    meta = metadata_from_json(metadata_to_json(extract_metadata(module, "gen.ritz")))
    resolver = ImportResolver(str(RITZ_ROOT), use_cache=False)
    resolver._register_items_from_metadata(meta, "gen.ritz")
    sys_enum = resolver.enums["Sys"]
    assert [v.discriminant for v in sys_enum.variants] == [0, 60]
