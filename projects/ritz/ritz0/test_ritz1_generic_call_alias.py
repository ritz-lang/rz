"""Regression tests for AGAST #2037 — a type alias as an explicit generic call
argument must mangle as its target type.

    type Id = u32
    struct D
        v: Vec<Id>                 # field type: Vec$u32 (alias resolved, #1475)
    fn f(d: *D) -> i64
        return vec_len<Id>(@d.v)   # call suffix: $Id  -> instantiates Vec$Id

ritz1 rejected this with

    argument 1 of `vec_len` has the wrong type: Vec$Id* != Vec$u32*

(tempest lib/document.ritz:184, `vec_len<NodeId>(@doc.free_list)`).  The
single-token generic-call rules (`f<T>(..)`, `f<*T>(..)`, `f<@T>(..)`) built
the suffix from the raw token text, bypassing the parse-time alias table that
type annotations go through.  A full type-argument list (`f<Pair<Id>>(..)`)
already parsed its arguments as type_spec and resolved them.

Every program exits with its expected code when the alias resolved.  ritz0 is
the oracle where it can be: it mangles an alias by NAME everywhere (`Vec$Id`,
`vec_len$Id`), so it accepts a program that spells the alias consistently but
rejects one mixing an alias with its target (or with another alias of it) —
RITZ0_MANGLES_ALIAS_NAME, strict xfail for ritz0 (AGAST #2049).
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

# The ticket's repro: field spelled with the alias, call spelled with the alias.
REPRO = """\
import ritzlib.memory
import ritzlib.gvec

type Id = u32

struct D
    v: Vec<Id>

fn f(d: *D) -> i64
    return vec_len<Id>(@d.v)

pub fn main() -> i32
    var d: D = D { v: vec_new<Id>() }
    vec_push<Id>(@d.v, 7)
    vec_push<Id>(@d.v, 9)
    vec_push<Id>(@d.v, 11)
    return f(@d) as i32
"""

# tempest's shape: a pub alias, a free list, and the element read back through
# vec_get<Alias> as the alias type.
FREE_LIST = """\
import ritzlib.memory
import ritzlib.gvec

pub type NodeId = u32

struct Doc
    free_list: Vec<NodeId>

fn take(doc: *Doc) -> NodeId
    let n: i64 = vec_len<NodeId>(@doc.free_list)
    return vec_get<NodeId>(@doc.free_list, n - 1)

pub fn main() -> i32
    var doc: Doc = Doc { free_list: vec_new<NodeId>() }
    vec_push<NodeId>(@doc.free_list, 2)
    vec_push<NodeId>(@doc.free_list, 5)
    return take(@doc) as i32
"""

# A user generic fn: the alias instantiates the same `bump$u32` as `u32`.
LOCAL_FN = """\
type Id = u32

fn bump<T>(x: T) -> T
    return x + 1

pub fn main() -> i32
    let a: Id = 1
    let b: u32 = bump<Id>(a)
    return bump<u32>(b) as i32
"""

# Alias of an alias, mixed with the target's own name and the middle alias.
CHAIN = """\
import ritzlib.memory
import ritzlib.gvec

type Raw = u32
type Id = Raw

struct D
    v: Vec<Raw>

pub fn main() -> i32
    var d: D = D { v: vec_new<u32>() }
    vec_push<Id>(@d.v, 1)
    vec_push<Raw>(@d.v, 2)
    let x: Id = vec_get<Id>(@d.v, 1)
    return (vec_len<Id>(@d.v) as i32) + (x as i32) - 1
"""

# `f<*Alias>(..)` — the pointer rule's suffix is `$ptr_<target>`.
POINTER = """\
import ritzlib.memory
import ritzlib.gvec

type Id = u32

struct D
    v: Vec<*u32>

pub fn main() -> i32
    var a: u32 = 3
    var d: D = D { v: vec_new<*u32>() }
    vec_push<*Id>(@d.v, @a)
    let p: *Id = vec_get<*Id>(@d.v, 0)
    return (vec_len<*Id>(@d.v) as i32) + (*p as i32) - 1
"""

# Nested: the alias inside a generic type argument (`Vec<Pair<Id>>`), mixed
# with the target spelling.  Goes through the full type-argument-list rule.
NESTED = """\
import ritzlib.memory
import ritzlib.gvec

type Id = u32

struct Pair<T>
    a: T
    b: T

struct D
    v: Vec<Pair<Id>>

pub fn main() -> i32
    var d: D = D { v: vec_new<Pair<u32>>() }
    vec_push<Pair<Id>>(@d.v, Pair<Id> { a: 1, b: 2 })
    let q: Pair<Id> = vec_get<Pair<Id>>(@d.v, 0)
    return (vec_len<Pair<Id>>(@d.v) as i32) + (q.b as i32)
"""

# `f<@Alias>(..)` — the reference rule.
REF = """\
type Id = u32

fn pick<T>(a: T, b: T) -> T
    return b

pub fn main() -> i32
    let x: Id = 1
    let y: Id = 3
    let r: @u32 = pick<@Id>(@x, @y)
    return *r as i32
"""

PROGRAMS = {
    "repro": (REPRO, 3),
    "ref": (REF, 3),
    "free_list": (FREE_LIST, 5),
    "local_fn": (LOCAL_FN, 3),
    "chain": (CHAIN, 3),
    "pointer": (POINTER, 3),
    "nested": (NESTED, 3),
}

# ritz0 mangles the alias name itself, so mixing spellings of one type is a
# type error there (AGAST #2049).  Strict: when ritz0 resolves aliases before
# mangling these XPASS and must be removed from this set.
RITZ0_MANGLES_ALIAS_NAME = set()


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(request, tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    if name in RITZ0_MANGLES_ALIAS_NAME:
        request.applymarker(
            pytest.mark.xfail(
                strict=True, reason="AGAST #2049: ritz0 mangles alias names"
            )
        )
    program, expected = PROGRAMS[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == expected


# Each single-token rule names the instantiation after the alias's TARGET.
# A self-consistent program (one spelling throughout) runs either way, so
# this checks the emitted symbol: `f<Id>` must call `one$u32`, never `one$Id`.
SPELLING = """\
type Id = u32
type Word = Id
type PU = *u32

struct Point
    x: i32

type Pt = Point

fn one<T>(x: T) -> T
    return x

pub fn main() -> i32
    var v: Id = 1
    let a: Id = one<Id>(v)
    let b: Id = one<Word>(v)
    let p: *Id = one<*Id>(@v)
    let r: @Id = one<@Id>(@v)
    let q: *u32 = one<PU>(@v)
    var pt: Pt = Point { x: 0 }
    let s: *Point = one<*Pt>(@pt)
    v = v + (s.x as u32) + *q - 1
    return (a + b + *p) as i32 - *r as i32
"""

SPELLING_SYMBOLS = {
    "plain": ("one$u32", "one$Id"),
    "alias_of_alias": ("one$u32", "one$Word"),
    "pointer": ("one$ptr_u32", "one$ptr_Id"),
    "reference": ("one$ref_u32", "one$ref_Id"),
    "alias_of_pointer": ("one$ptr_u32", "one$PU"),
    "alias_of_struct": ("one$ptr_Point", "one$ptr_Pt"),
}


@pytest.mark.integration
@pytest.mark.parametrize("form", sorted(SPELLING_SYMBOLS))
def test_ritz1_alias_call_suffix_is_target(ritz1_bin, tmp_path, form):
    """AGAST #2037: the call suffix spells the alias's target type."""
    src = tmp_path / "main.ritz"
    src.write_text(SPELLING)
    ll = tmp_path / "main.ll"
    comp = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    ir = ll.read_text()
    want, unwanted = SPELLING_SYMBOLS[form]
    assert f"@{want}(" in ir, f"no call to {want}"
    assert f"@{unwanted}(" not in ir, f"{unwanted} mangled by alias name"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_generic_call_alias_arg(ritz1_bin, tmp_path, name):
    """AGAST #2037. Before the fix: `wrong type: Vec$Id* != Vec$u32*`."""
    program, expected = PROGRAMS[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == expected
