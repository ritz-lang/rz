"""Regression tests for AGAST #1598: ritz1 must parse a struct field whose type
is a mutable borrow:

    struct R
        ch:& C

ritz1 lexes `:&` as COLON AMP. `param` gained an `IDENT COLON AMP type_spec`
alternative in #1301/#1522, but `struct_field` stayed `IDENT COLON type_spec`
only, so the struct failed to parse and the item anchor-skip reported

    cannot parse item starting at 'struct R'

which is how tempest's lib/tab_renderer.ritz:22 died under ritz1. The fix adds
the AMP form to `struct_field` and lowers it to type_mut_ref (`@&C`), the same
type ritz0 gives it. Struct-style enum variants reuse `struct_fields` (#1543),
so they accept the form too.

#2041 taught the ritz1 emitter to initialise, read and write through such a
field (and through `@C` / `@&C` fields): they are laid out as `ptr` and member
access through them auto-derefs like a `*C` field.

#2050 did the same for ref fields to an integer (`p: @i32` / `@&u8` /
`p:& i64`): they lower to a `*T` field. #2053 made `*f64` / `*f32` / `*bool`
fields load and store at their own width, so float and bool refs lower too.

Every program returns 3 on success. ritz0 is the oracle.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


# --- programs -----------------------------------------------------------------

# The ticket's repro, verbatim.
REPRO = """\
struct C
    x: i32
struct R
    ch:& C
pub fn main() -> i32
    return 3
"""

# Borrow fields mixed with plain fields before, between and after, plus a
# generic struct and an item after them. A borrow field that swallowed the
# following field or item would fail to compile or change the answer.
MIXED_FIELDS = """\
struct C
    x: i32

struct TabRenderer
    id: i32
    channel:& C
    count: i32
    other:& C

struct Holder<T>
    item:& T
    n: i32

struct After
    v: i32

pub fn main() -> i32
    let a: After = After { v: 3 }
    return a.v
"""

# Read and write a field through the borrow, both directly and via a pointer
# to the outer struct: c.x goes 1 -> 2 (in bump) -> 3 (in main).
READ_WRITE = """\
struct C
    x: i32

struct R
    ch:& C

fn bump(r: *R)
    r.ch.x = r.ch.x + 1

pub fn main() -> i32
    var c: C = C { x: 1 }
    var r: R = R { ch: @&c }
    bump(@r)
    r.ch.x = r.ch.x + 1
    return c.x
"""

# Read-only use: the value read through the borrow reaches the exit code.
READ_ONLY = """\
struct C
    x: i32

struct R
    ch:& C

fn get(r: *R) -> i32
    return r.ch.x

pub fn main() -> i32
    var c: C = C { x: 3 }
    var r: R = R { ch: @&c }
    return get(@r)
"""

PROGRAMS = {
    "repro": REPRO,
    "mixed_fields": MIXED_FIELDS,
}

# A ref field between plain fields: the struct literal must put each value in
# its own slot and the ref field must be pointer-sized, or `tail` reads junk.
# Also writes through a ref field of a by-value local and passes the inner
# pointer on to a callee expecting `*C`.
MIXED_ACCESS = """\
struct C
    x: i32
    y: i64

struct R
    head: i32
    ch:& C
    tail: i64

fn set_y(c: *C, v: i64)
    c.y = v

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var r: R = R { head: 1, ch: @&c, tail: 1 }
    r.ch.x = r.ch.x + r.head
    set_y(r.ch, r.tail)
    return (r.ch.x as i64 + c.y) as i32
"""

# A plain `*C` field initialised from `@&c`. `@&c` is a `ptr` in ritz1, not
# the i64 its pointer model uses, so the struct literal must not inttoptr it
# (#2041 found this; a ref field's literal takes the same path).
PTR_FIELD_FROM_BORROW = """\
struct C
    x: i32

struct P
    ch: *C

pub fn main() -> i32
    var c: C = C { x: 2 }
    var p: P = P { ch: @&c }
    p.ch.x = p.ch.x + 1
    return c.x
"""

# Field access through the borrow (#2041). ritz0 is the oracle. Each program
# also runs with the field spelled `@C` and `@&C`; ritz0 and ritz1 lower all
# three spellings to a pointer.
_ACCESS_BASE = {
    "read_write": READ_WRITE,
    "read_only": READ_ONLY,
    "mixed": MIXED_ACCESS,
}
_FIELD_SPELLINGS = {
    "colon_amp": ":& C",
    "at": ": @C",
    "at_amp": ": @&C",
}
ACCESS = {
    "ptr_field_from_borrow": PTR_FIELD_FROM_BORROW,
} | {
    f"{name}_{spelling}": re.sub(r":& C$", ty, prog, flags=re.MULTILINE)
    for name, prog in _ACCESS_BASE.items()
    for spelling, ty in _FIELD_SPELLINGS.items()
    if name == "read_only" or spelling != "at"   # an `@T` is read-only (#2338)
}

# Ref fields to a primitive (#2050). #2041 lowered ref-to-struct fields only;
# a ref-to-primitive field failed closed with "struct literal field of this
# type is not lowered". Each program is instantiated for i32/u8/i64 and each
# field spelling. `T` is the pointee, `FIELD` the field's type.

# The ticket's repro: read through the field.
PRIM_READ = """\
struct R
    p FIELD

pub fn main() -> i32
    var x: T = 3
    var r: R = R { p: @&x }
    return *r.p as i32
"""

# Write through the field, directly and via a pointer to the outer struct:
# x goes 1 -> 2 (in bump) -> 3 (in main).
PRIM_WRITE = """\
struct R
    p FIELD

fn bump(r: *R)
    *r.p = *r.p + 1

pub fn main() -> i32
    var x: T = 1
    var r: R = R { p: @&x }
    bump(@r)
    *r.p = *r.p + 1
    return x as i32
"""

# The ref field sits between plain fields of other widths: it must be
# pointer-sized and the literal must fill each slot, or head/tail read junk.
# Also passes the field on to a callee expecting `*T`.
PRIM_MIXED = """\
struct R
    head: u8
    p FIELD
    tail: i64

fn peek(q: *T) -> T
    return *q

pub fn main() -> i32
    var x: T = 1
    var r: R = R { head: 1, p: @&x, tail: 1 }
    *r.p = *r.p + r.head as T
    return (peek(r.p) as i64 + r.tail) as i32
"""

_PRIM_BASE = {"read": PRIM_READ, "write": PRIM_WRITE, "mixed": PRIM_MIXED}
_PRIM_SPELLINGS = {"colon_amp": ":& T", "at": ": @T", "at_amp": ": @&T"}
PRIM_ACCESS = {
    f"{name}_{spelling}_{ty}": prog.replace("FIELD", field).replace("@&x", "@x" if field.startswith(": @") and "&" not in field else "@&x").replace("T", ty)
    for name, prog in _PRIM_BASE.items()
    for spelling, field in _PRIM_SPELLINGS.items()
    for ty in ("i32", "u8", "i64")
    if name == "read" or spelling != "at"   # an `@T` is read-only (#2338)
}

# Ref fields to f32 / f64 / bool (#2053). Until `*f64` fields loaded and stored
# at their own width these stayed fail-closed; now they lower to `*T` like the
# integer refs above. Float programs use float literals (`*r.p + 1` is a type
# error in ritz0). x goes 0.5 -> 1.75 (in bump) -> 3.0 (in main).
FLOAT_REF_WRITE = """\
struct R
    p FIELD

fn bump(r: *R)
    *r.p = *r.p + 1.25

pub fn main() -> i32
    var x: T = 0.5
    var r: R = R { p: @&x }
    bump(@r)
    *r.p = *r.p + 1.25
    return x as i32
"""

# Between fields of other widths, read back through the field and a `*T`
# callee, and the struct literal initialised with `@x`.
FLOAT_REF_MIXED = """\
struct R
    head: u8
    p FIELD
    tail: i64

fn peek(q: *T) -> T
    return *q

pub fn main() -> i32
    var x: T = 1.5
    var r: R = R { head: 1, p: @&x, tail: 1 }
    *r.p = *r.p - 0.5
    return (peek(r.p) as i64 + r.head as i64 + r.tail) as i32
"""

# A bool ref into an `i1` struct field with neighbours: a wide store through
# the field would clobber `after`.
BOOL_REF = """\
struct S
    b: bool
    after: u8

struct R
    p FIELD

fn flip(r: *R)
    *r.p = not *r.p

pub fn main() -> i32
    var s: S = S { b: false, after: 3 }
    var r: R = R { p: @&s.b }
    flip(@r)
    if *r.p and s.b
        return s.after as i32
    return 100
"""

# An `@T` field only reads (#2338), at each width, with neighbours.
NONINT_REF_READ = """\
struct R
    head: u8
    p: @T
    tail: i64

pub fn main() -> i32
    var x: T = VALUE
    let r: R = R { head: 1, p: @x, tail: 1 }
    if *r.p == VALUE
        return r.head as i32 + r.tail as i32 + 1
    return 100
"""

_NONINT_SPELLINGS = {"colon_amp": ":& {t}", "at_amp": ": @&{t}"}
NONINT_REF_ACCESS = {
    f"read_at_{ty}": NONINT_REF_READ.replace("T", ty).replace("VALUE", value)
    for ty, value in (("f64", "1.5"), ("f32", "1.5"), ("bool", "true"))
} | {
    f"{name}_{spelling}_{ty}": prog.replace("FIELD", field.format(t=ty)).replace(
        "T", ty
    )
    for name, prog in {"write": FLOAT_REF_WRITE, "mixed": FLOAT_REF_MIXED}.items()
    for spelling, field in _NONINT_SPELLINGS.items()
    for ty in ("f64", "f32")
} | {
    f"bool_{spelling}": BOOL_REF.replace("FIELD", field.format(t="bool"))
    for spelling, field in _NONINT_SPELLINGS.items()
}

# The borrow field must lower to a reference (pointer-sized), not to the
# pointee: `ch:& C` parsed as plain `C` would embed {i32, i64} inline.
LAYOUT = """\
struct C
    x: i32
    y: i64
struct R
    ch:& C
fn f(r: *R) -> i32
    return 3
pub fn main() -> i32
    return 3
"""

# Struct-style enum variants share `struct_fields` in ritz1 (#1543), so they
# accept a borrow field too. Tag indices must still count the variant: Stop is
# 1 and GoBack is 3, so the answer is 1 + 2 = 3.
#
# ritz0's variant-field loop took only COLON until #2040, so it rejected this
# program; it now accepts COLON_AMP exactly as its struct-field parser does.
ENUM_VARIANT = """\
struct C
    x: i32

enum Msg
    Attach
        channel:& C
    Stop
    Bind
        id: i32
        ch:& C
    GoBack

fn code(m: Msg) -> i32
    match m
        Stop => 1
        GoBack => 2
        _ => 100

pub fn main() -> i32
    return code(Msg.Stop) + code(Msg.GoBack)
"""

# A 32-byte C: a by-value field would make the payload [32 x i8]; a reference
# makes it [8 x i8]. Distinguishes "parsed `:&` as `:`" from "wrapped in a ref".
VARIANT_LAYOUT = """\
struct C
    a: i64
    b: i64
    c: i64
    d: i64

enum Msg
    Attach
        channel:& C
    Stop

pub fn main() -> i32
    return 3
"""

# `ch: &C` (spaced) is NOT the borrow form. ritz0 lexes `:&` as one COLON_AMP
# token, so `: &C` is the removed legacy `&T` reference type and gets a
# migration diagnostic. ritz1 lexes `:&` as COLON AMP and cannot tell the two
# apart, the same known looseness as `param` (#1301, #1522). Pinned on the
# ritz0 side only.
SPACED_LEGACY = """\
struct C
    x: i32
struct R
    ch: &C
pub fn main() -> i32
    return 3
"""

# Malformed borrow fields must still be rejected.
MALFORMED = {
    "borrow_missing_type": """\
struct R
    ch:&
pub fn main() -> i32
    return 3
""",
    "borrow_missing_colon": """\
struct C
    x: i32
struct R
    ch & C
pub fn main() -> i32
    return 3
""",
}


def _compile(compiler: str, ritz1_bin, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        cmd = [str(ritz1_bin), str(src), "-o", str(ll)]
        comp = subprocess.run(
            cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
        )
    return comp, ll, work


def _run(compiler: str, ritz1_bin, tmp_path: Path, name: str, program=None) -> int:
    """Compile PROGRAMS[name] (or `program`) with `compiler`, link, run, return
    the exit code."""
    if program is None:
        program = PROGRAMS[name]
    comp, ll, work = _compile(compiler, ritz1_bin, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", None, tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_struct_field_borrow(ritz1_bin, tmp_path, name):
    """AGAST #1598. Before the fix these died with `cannot parse item`."""
    assert _run("ritz1", ritz1_bin, tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ACCESS))
def test_ritz0_borrow_field_access(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, ACCESS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ACCESS))
def test_ritz1_borrow_field_access(ritz1_bin, tmp_path, name):
    """AGAST #2041. Before the fix: "struct literal field of this type is not
    lowered" / "unhandled EXPR_MEMBER"."""
    assert _run("ritz1", ritz1_bin, tmp_path, name, ACCESS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PRIM_ACCESS))
def test_ritz0_prim_ref_field_access(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, PRIM_ACCESS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PRIM_ACCESS))
def test_ritz1_prim_ref_field_access(ritz1_bin, tmp_path, name):
    """AGAST #2050. Before the fix: "struct literal field of this type is not
    lowered"."""
    assert _run("ritz1", ritz1_bin, tmp_path, name, PRIM_ACCESS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("ty", ["i32", "u8", "i64", "f64", "f32", "bool"])
def test_ritz1_prim_ref_field_is_a_reference(ritz1_bin, tmp_path, ty):
    """A `p: @T` field is laid out as `ptr`, as in ritz0, not as `T`."""
    prog = f"struct R\n    p: @{ty}\n\npub fn main() -> i32\n    return 3\n"
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, f"layout_{ty}", prog)
    assert comp.returncode == 0 and ll.exists(), comp.stderr[-2000:]
    m = re.search(r"^%R = type (.*)$", ll.read_text(), re.MULTILINE)
    assert m, "no %R type in ritz1 IR"
    assert m.group(1).replace(" ", "") == "{ptr}", m.group(1)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NONINT_REF_ACCESS))
def test_ritz0_nonint_ref_field_access(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, NONINT_REF_ACCESS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NONINT_REF_ACCESS))
def test_ritz1_nonint_ref_field_access(ritz1_bin, tmp_path, name):
    """AGAST #2053. #2050 kept float / bool refs fail-closed ("struct literal
    field of this type is not lowered") because a `*f64` field loaded `i8`
    and stored `i64 %double`."""
    assert _run("ritz1", ritz1_bin, tmp_path, name, NONINT_REF_ACCESS[name]) == 3


@pytest.mark.integration
def test_ritz1_borrow_field_is_a_reference(ritz1_bin, tmp_path):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, "layout", LAYOUT)
    assert comp.returncode == 0 and ll.exists(), comp.stderr[-2000:]
    m = re.search(r"^%R = type (.*)$", ll.read_text(), re.MULTILINE)
    assert m, "no %R type in ritz1 IR"
    # #2041: ref fields lower like `*C` fields, i.e. to `ptr` as in ritz0.
    assert m.group(1).replace(" ", "") == "{ptr}", (
        f"`ch:& C` should lower to a reference, got %R = type {m.group(1)}"
    )


@pytest.mark.integration
def test_ritz1_enum_variant_borrow_field(ritz1_bin, tmp_path):
    """Struct-style variants reuse struct_fields, so `name:& T` parses there
    too and the variant still counts toward later tags."""
    assert _run("ritz1", ritz1_bin, tmp_path, "enum_variant", ENUM_VARIANT) == 3


@pytest.mark.integration
def test_ritz0_enum_variant_borrow_field(tmp_path):
    """AGAST #2040. Before the fix: "Expected ':' after field name 'channel'
    in enum variant 'Attach'"."""
    assert _run("ritz0", None, tmp_path, "enum_variant", ENUM_VARIANT) == 3


@pytest.mark.integration
def test_ritz0_enum_variant_borrow_field_is_a_reference(tmp_path):
    """`channel:& C` in a variant is a reference, as in a struct body: the
    payload holds a pointer, not the 32-byte C."""
    comp, ll, _ = _compile("ritz0", None, tmp_path, "variant_layout", VARIANT_LAYOUT)
    assert comp.returncode == 0 and ll.exists(), comp.stdout[-2000:] + comp.stderr[-2000:]
    m = re.search(r'^%"enum\.[^"]*\.Msg" = type (.*)$', ll.read_text(), re.MULTILINE)
    assert m, "no Msg enum type in ritz0 IR"
    assert m.group(1).replace(" ", "") == "{i8,[7xi8],[8xi8]}", (
        f"`channel:& C` should lower to a reference, got Msg = type {m.group(1)}"
    )


@pytest.mark.integration
def test_ritz0_rejects_spaced_legacy_field(tmp_path):
    comp, _, _ = _compile("ritz0", None, tmp_path, "spaced", SPACED_LEGACY)
    assert comp.returncode != 0
    assert "Legacy `&T` reference syntax" in comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_malformed_borrow_field(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed borrow field {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
