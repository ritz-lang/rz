"""ritz0 monomorph infers an un-annotated local from a method-call initializer
(AGAST #2095).

    var s = a.slice(0, n)     # impl<T> Vec<T>'s slice -> Vec<T>
    var s = a[:]              # slice sugar on a Vec<T>
    var v = b.items()         # user impl method -> Vec<i32>
    var w = p.dup()           # generic impl method, substituted at W<i32>
    var t = s.slice(0, 1)     # chain through an inferred local

`_infer_value_type` knew none of these, so `s` was untyped and a generic
method reached only through it (`s.pop()`) was never instantiated: ritz0 then
failed "No method 'pop' found for type 'Vec$i32'".

Each case runs the monomorphizer on a self-contained module (a stub `Vec<T>`,
the `vec_*` functions and the `impl<T> Vec<T>` wrappers ritzlib's gvec has)
and checks the method used only through the inferred local was specialised at
i32: its wrapper `Vec$i32.pop`, and through it `vec_pop<i32>`.

Method syntax reaches only impl methods (LARB R66), so the free fn behind a
method is instantiated only by specialising the wrapper that calls it.  The
`vec_` prefix table that used to pre-instantiate it from `v.pop()` directly
went with AGAST #4303; test_free_fn_without_wrapper_is_not_instantiated pins
that.  The end-to-end programs are in test_ritz1_method_init_infer.py.
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

impl<T> Vec<T>
    pub fn slice(self: *Vec<T>, start: i64, end: i64) -> Vec<T>
        return vec_slice<T>(self, start, end)
    pub fn len(self: *Vec<T>) -> i64
        return vec_len<T>(self)
    pub fn pop(self: *Vec<T>) -> T
        return vec_pop<T>(self)
    pub fn last(self: *Vec<T>) -> T
        return vec_last<T>(self)
"""


def _monomorphize(body: str) -> Monomorphizer:
    mono = Monomorphizer()
    mono.monomorphize(parse(PRELUDE + body))
    return mono


def _instantiated(body: str) -> set:
    return set(_monomorphize(body).function_instantiations)


def _pop_wrapper_specialised(mono: Monomorphizer) -> bool:
    return ("Vec", ("i32",), "pop") in mono._done_methods


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
    mono = _monomorphize(CASES[name])
    assert _pop_wrapper_specialised(mono), name
    # The wrapper's body names vec_pop<i32>: instantiated transitively.
    assert ("vec_pop", ("i32",)) in mono.function_instantiations, name


@pytest.mark.unit
def test_free_fn_without_wrapper_is_not_instantiated():
    """`a.first()` has no `impl Vec<T>` wrapper, so it names no method: the
    free fn `vec_first<T>` is not pre-instantiated behind it, as the `vec_`
    prefix table did (AGAST #4303)."""
    got = _instantiated("""
fn vec_first<T>(v: *Vec<T>) -> T
    return *v.data

fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    return a.first()
""")
    assert not any(name == "vec_first" for name, _ in got)


@pytest.mark.unit
def test_no_ufcs_prefix_table():
    """The UFCS instantiation table and its registrars are gone (#4303)."""
    for attr in ("TYPE_TO_UFCS_PREFIX", "_register_ufcs_instantiation",
                 "_register_method_instantiation"):
        assert not hasattr(Monomorphizer, attr), attr


@pytest.mark.unit
def test_unresolvable_method_leaves_local_untyped():
    """An unknown method must not invent a type (and must not crash): `s`
    stays untyped, so `s.pop()` is wanted on every instance (a wild method),
    never as `Vec<i32>.pop` from a type `nonexistent` doesn't have."""
    mono = _monomorphize("""
fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    var s = a.nonexistent()
    return s.pop()
""")
    assert ("Vec", ("i32",), "pop") not in mono._wanted_methods
    assert "pop" in mono._wild_methods
