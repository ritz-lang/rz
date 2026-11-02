"""AGAST #2049: a type alias in a generic argument mangles as its target.

    type Raw = u32
    type Id = Raw
    struct D
        v: Vec<Raw>
    ... vec_push<Id>(@d.v, 1)

ritz0 mangled the alias's own name (`Vec$Id`, `vec_push$Id`), so mixing an
alias with its target was `Vec$Id* != Vec$Raw*`.  Aliases are transparent:
every spelling of one type must be one instantiation, `$u32`, which is also
what ritz1 emits (#2037).  End-to-end programs (chain, pointer, nested) live in
test_ritz1_generic_call_alias.py; these pin the monomorphizer's mangling.
"""

import pytest

import ritz_ast as rast
from monomorph import mangle_type_name, monomorphize
from parser import parse

pytestmark = pytest.mark.unit


def _names(source):
    """Struct and fn names after monomorphizing `source`."""
    result = monomorphize(parse(source))
    return {
        item.name
        for item in result.items
        if isinstance(item, (rast.StructDef, rast.FnDef))
    }


def test_alias_chain_mixed_with_target_is_one_instantiation():
    names = _names("""
type Raw = u32
type Id = Raw

struct Box<T>
    x: T

fn put<T>(b: *Box<T>, v: T) -> i32
    b.x = v
    0

struct D
    b: Box<Raw>

fn main() -> i32
    var d: D = D { b: Box<u32> { x: 0 } }
    put<Id>(@d.b, 1)
    put<Raw>(@d.b, 2)
    0
""")
    assert {"Box$u32", "put$u32"} <= names
    assert not {n for n in names if n.endswith(("$Id", "$Raw"))}


def test_alias_under_pointer_mangles_as_target():
    names = _names("""
type Id = u32

fn one<T>(x: T) -> T
    x

fn main() -> i32
    var a: u32 = 1
    one<*Id>(@a)
    one<*u32>(@a)
    0
""")
    assert "one$ptr_u32" in names
    assert "one$ptr_Id" not in names


def test_alias_nested_in_generic_arg_mangles_as_target():
    names = _names("""
type Id = u32

struct Pair<T>
    a: T

struct Box<T>
    x: T

struct D
    b: Box<Pair<Id>>

fn main() -> i32
    var d: D = D { b: Box<Pair<u32>> { x: Pair<u32> { a: 1 } } }
    0
""")
    assert {"Box$Pair_u32", "Pair$u32"} <= names
    assert "Box$Pair_Id" not in names


def test_union_alias_keeps_its_name():
    """A union alias is nominal in ritz0 (its own LLVM struct), not a spelling."""
    names = _names("""
type IU = i32 | i64

fn one<T>(x: T) -> T
    x

fn main() -> i32
    let v: IU = 1 as i32
    one<IU>(v)
    0
""")
    assert "one$IU" in names


def test_alias_table_does_not_outlive_the_pass():
    monomorphize(parse("type Id = u32\n\nfn main() -> i32\n    0\n"))
    assert mangle_type_name(rast.NamedType(None, "Id", [])) == "Id"
