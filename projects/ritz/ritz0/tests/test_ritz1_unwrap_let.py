"""AGAST #2576: an un-annotated `let t = r.unwrap()` takes the payload's type.

    fn mk() -> Result<Vec<E>, i32>
    let tables = mk().unwrap()
    assert tables.len() == 2          # ritz1: "cannot determine receiver type"
    assert tables[0].offset == 64     # ritz1: "unhandled EXPR_MEMBER"

`.unwrap()` on an Option / Result is ritz1's try_emit_enum_unwrap intrinsic,
which has no FnDef, so the let's EXPR_METHOD arm found no return type and
left the slot i64: every use of `t` was refused, unlocated.  angelo's
loader/ttf.ritz [[test]] fns hit it (`parse_table_directory(..).unwrap()`).

ritz0 compiles [[test]] fns into a bin build too (as `internal` fns), so ritz1
compiling them is right; the gap was the type.  ritz0 is the oracle: every row
exits 0, and a failed check returns its own number.
"""

import pytest

from test_ritz1_for_header import COMPILERS, compile_with, run_with  # noqa: F401  (fixtures)

pytestmark = pytest.mark.batched

_TYPES = """\
import ritzlib.gvec

struct Tag
    v: u32

impl Tag
    pub fn eq({self}, o: Tag) -> bool
        self.v == o.v

struct E
    tag: Tag
    offset: u32

struct H
    k: u32

impl H
    pub fn res(self: @H) -> Result<{P}, i32>
        Ok({make_self})

    pub fn opt(self: @H) -> Option<{P}>
        Some({make_self})

fn mk_res(k: u32) -> Result<{P}, i32>
    Ok({make_k})

fn mk_opt(k: u32) -> Option<{P}>
    Some({make_k})

"""

# How a payload is built from `k`, and how main checks it.  Tag.eq takes
# `self` by value, as angelo's types.ritz does.  E is a struct
# whose first field is itself a struct with a method; Vec<E> is a generic
# instance (`%Vec$E`), indexed then read through.
PAYLOADS = {
    "struct": (
        "E",
        "E {{ tag: Tag {{ v: {k} }}, offset: {k} + 1 }}",
        """\
    if not t.tag.eq(Tag { v: 7 })
        return 1
    if t.offset != 8
        return 2
""",
    ),
    "vec": (
        "Vec<E>",
        "vec_of({k})",
        """\
    if t.len() != 2
        return 1
    if not t[0].tag.eq(Tag { v: 7 })
        return 2
    if t[1].offset != 64
        return 3
""",
    ),
}

_VEC_OF = """\
fn vec_of(k: u32) -> Vec<E>
    var v: Vec<E> = vec_new<E>()
    v.push(E { tag: Tag { v: k }, offset: k + 1 })
    v.push(E { tag: Tag { v: 2 }, offset: 64 })
    v

"""

# Where the Option / Result comes from: a free fn's result, a method's, or
# a local already bound to one.
SOURCES = {
    "call": ("", "mk_{c}(7)"),
    "method": ("    let h = H {{ k: 7 }}\n", "h.{c}()"),
    "local": ("    let r = mk_{c}(7)\n", "r"),
}


def _program(payload: str, carrier: str, source: str, recv: str = "self") -> str:
    ty, make, checks = PAYLOADS[payload]
    head = _TYPES.format(
        self=recv, P=ty, make_k=make.format(k="k"), make_self=make.format(k="self.k")
    )
    if payload == "vec":
        head += _VEC_OF
    pre, src = SOURCES[source]
    return (
        head
        + "pub fn main() -> i32\n"
        + pre.format(c=carrier)
        + f"    let t = {src.format(c=carrier)}.unwrap()\n"
        + checks
        + "    0\n"
    )


# Payload x source on Result; Option on the call path only: the carrier
# changes the payload lookup's family, not where the receiver's type comes from.
ROWS = [(p, "res", s) for p in PAYLOADS for s in SOURCES] + [
    (p, "opt", "call") for p in PAYLOADS
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("payload,carrier,source", ROWS)
def test_unwrap_let_takes_payload_type(run_with, payload, carrier, source, compiler):
    name = f"unwrap_{payload}_{carrier}_{source}"
    assert run_with(compiler, name, _program(payload, carrier, source)) == 0


# `self: @Tag` borrows `t[0].tag`, so its address is taken: the lvalue path
# must know `t` is a Vec<E> to index its heap buffer.  ritz0 recorded no Ritz
# type for `let t = x.unwrap()` (an intrinsic, with no FnDef to read a return
# type off), and crashed "Cannot index type: %Vec$E" (#3237).  Every source
# and carrier the ticket names; the payload is the Vec one that indexes.
BORROWED_ROWS = [("res", s) for s in SOURCES] + [("opt", "call")]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("carrier,source", BORROWED_ROWS)
def test_unwrap_let_borrowed_receiver(run_with, carrier, source, compiler):
    program = _program("vec", carrier, source, recv="self: @Tag")
    name = f"unwrap_borrowed_{carrier}_{source}"
    assert run_with(compiler, name, program) == 0


# `.unwrap_or(d)` is the same intrinsic and takes the same payload type.
# ritz1 left that let untyped ("cannot determine receiver type") and selected
# the payload against the default as i64s (#3250).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_unwrap_or_let_borrowed_receiver(run_with, compiler):
    program = _program("vec", "res", "call", recv="self: @Tag").replace(
        ".unwrap()", ".unwrap_or(vec_of(9))")
    assert run_with(compiler, "unwrap_or_borrowed", program) == 0


# AGAST #4458: the same let takes the payload's type when that payload is a
# reference or pointer (`Option<@Font>`, `Option<@&Font>`, `Option<*Font>`,
# and the Result forms).  The mangled payload names are `ref_` / `refmut_` /
# `ptr_`, which the emitter's struct-payload rule did not read, so the local
# stayed i64: reading it was "unhandled EXPR_MEMBER" and passing it to a
# `:&` / `@` parameter was "this place doesn't hold what the `:&` parameter
# borrows".  prism's `test_text_rendering.ritz` hit it through
# `mgr.get_mut(id).unwrap()` (`Option<@&Font>`).
#
# Each row exercises both uses a single local gets: a field read (`x.size`)
# and the argument to a parameter taking the pointer (`@Font` by value,
# `:& Font`, `*Font`), so the emitter's slot and Sema's place image must agree.
_PTR_TYPES = """\
struct Font
    size: i32

fn mk_opt_ref(p: @Font) -> Option<@Font>
    Some(p)

fn mk_opt_mut(p: @&Font) -> Option<@&Font>
    Some(p)

fn mk_opt_ptr(p: *Font) -> Option<*Font>
    Some(p)

fn mk_res_ref(p: @Font) -> Result<@Font, i32>
    Ok(p)

fn mk_res_mut(p: @&Font) -> Result<@&Font, i32>
    Ok(p)

fn mk_res_ptr(p: *Font) -> Result<*Font, i32>
    Ok(p)

fn take_ref(p: @Font) -> i32
    p.size

fn take_mut(p:& Font) -> i32
    p.size

fn take_ptr(p: *Font) -> i32
    p.size

"""

# Payload spelling -> how main builds it from `f` and how it is passed on.
_PTR_PAYLOADS = {
    "ref": ("@f", "take_ref"),
    "mut": ("@&f", "take_mut"),
    "ptr": ("@f", "take_ptr"),
}


def _ptr_program(carrier: str, payload: str) -> str:
    arg, take = _PTR_PAYLOADS[payload]
    return (
        _PTR_TYPES
        + "pub fn main() -> i32\n"
        + "    var f: Font = Font { size: 7 }\n"
        + f"    let r = mk_{carrier}_{payload}({arg})\n"
        + "    let x = r.unwrap()\n"
        + "    if x.size != 7\n"
        + "        return 1\n"
        + f"    if {take}(x) != 7\n"
        + "        return 2\n"
        + "    0\n"
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("carrier", ["opt", "res"])
@pytest.mark.parametrize("payload", sorted(_PTR_PAYLOADS))
def test_unwrap_let_takes_pointer_payload_type(run_with, carrier, payload, compiler):
    name = f"unwrap_ptr_{carrier}_{payload}"
    assert run_with(compiler, name, _ptr_program(carrier, payload)) == 0
