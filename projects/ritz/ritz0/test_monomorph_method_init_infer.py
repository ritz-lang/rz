"""ritz0 monomorph infers an un-annotated local from a method-call initializer
(AGAST #2095).

    var s = a.slice(0, n)     # UFCS: vec_slice<T> -> Vec<T>
    var s = a[:]              # slice sugar on a Vec<T>
    var v = b.items()         # user impl method -> Vec<i32>
    var w = p.dup()           # generic impl method, substituted at W<i32>
    var t = s.slice(0, 1)     # chain through an inferred local

`_infer_value_type` knew none of these, so `s` was untyped and a generic
method reached only through it (`s.pop()`) was never instantiated: ritz0 then
failed "No method 'pop' found for type 'Vec$i32'".

Each case runs the instantiation pass on a self-contained module (a stub
`Vec<T>` and the `vec_*` functions it needs) and checks the method used only
through the inferred local was registered at i32.  The end-to-end programs are
in test_ritz1_method_init_infer.py.
"""

import pytest

from monomorph import Monomorphizer
from parser import parse

PRELUDE = """
struct Vec<T>
    data: *T
    len: i64

fn vec_new<T>() -> Vec<T>
    return Vec<T> { data: null, len: 0 }

fn vec_slice<T>(v: *Vec<T>, start: i64, end: i64) -> Vec<T>
    return vec_new<T>()

fn vec_len<T>(v: *Vec<T>) -> i64
    return v.len

fn vec_pop<T>(v: *Vec<T>) -> T
    return *v.data

fn vec_last<T>(v: *Vec<T>) -> T
    return *v.data
"""


def _instantiated(body: str) -> set:
    mono = Monomorphizer()
    module = parse(PRELUDE + body)
    mono._collect_generics(module)
    mono._find_instantiations(module)
    return {(name, args) for (name, args) in mono.function_instantiations}


CASES = {
    "ufcs_slice": """
fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    var s = a.slice(0, 1)
    return s.pop()
""",
    "full_slice_sugar": """
fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    var s = a[:]
    return s.pop()
""",
    "chain": """
fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    var s = a[:]
    var t = s.slice(0, 1)
    return t.pop()
""",
    "impl_method": """
struct Bag
    n: i32

impl Bag
    fn items(self: *Bag) -> Vec<i32>
        return vec_new<i32>()

fn main() -> i32
    var b: Bag = Bag { n: 1 }
    var v = b.items()
    return v.pop()
""",
    "generic_impl_method": """
struct W<T>
    v: Vec<T>

impl<T> W<T>
    fn inner(self: *W<T>) -> Vec<T>
        return self.v

fn main() -> i32
    var w: W<i32> = W<i32> { v: vec_new<i32>() }
    var v = w.inner()
    return v.pop()
""",
    "let_binding": """
fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    let s = a.slice(0, 1)
    return s.pop()
""",
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(CASES))
def test_method_reached_only_through_inferred_local_is_instantiated(name):
    assert ("vec_pop", ("i32",)) in _instantiated(CASES[name]), name


@pytest.mark.unit
def test_unresolvable_method_leaves_local_untyped():
    """An unknown method must not invent a type (and must not crash)."""
    got = _instantiated("""
fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    var s = a.nonexistent()
    return s.pop()
""")
    assert not any(name == "vec_pop" for name, _ in got)
