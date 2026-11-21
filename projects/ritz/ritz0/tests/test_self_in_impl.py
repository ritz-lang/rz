"""`Self` in an impl block is the impl's type (AGAST #2258).

THE DEFECT

ritz0 left a method signature's `Self` as a bare name nothing resolved, so it
lowered to i8: `fn get(self:= Self)` in `impl P` died in the emitter with
`TypeError: Type of #1 arg mismatch: i8 != %"struct...P"`, and `self: @Self`
with `Cannot access field on non-struct pointer: i8`. The parser now spells
`Self` as the impl's type in each method's parameters and return type, so every
later pass sees `P`. Trait impls get the same rule (LANGUAGE_SPEC §12 writes
the trait's `self: @Self` as `self: @Point` in the impl; either spelling is
the same type).

That a `self` typed `Self` is move-only, and moves when passed on, is pinned
by TestByValueReceiver in test_move_checker.py.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

pytestmark = pytest.mark.integration

# ritz1 spells `Self` as the impl's type too, and parses `self:= T` (AGAST
# #3249): before, a `self:= T` dropped the whole impl ("unexpected '='"), and
# all but a lent receiver in a non-generic impl was `unhandled EXPR_MEMBER`.

# name -> (program, exit status)
CASES = {
    # The ticket's program.
    "move": ("""\
struct P
    x: i32

impl P
    fn get(self:= Self) -> i32
        return self.x

pub fn main() -> i32
    var p = P { x: 3 }
    return p.get()
""", 3),
    "value": ("""\
struct P
    x: i32

impl P
    fn get(self: Self) -> i32
        return self.x

pub fn main() -> i32
    var p = P { x: 3 }
    return p.get()
""", 3),
    # Lent receivers, a `Self` argument and a `Self` return.
    "lent": ("""\
struct P
    x: i32

impl P
    fn bump(self: @&Self, by: @Self) -> Self
        self.x = self.x + by.x
        return P { x: self.x * 10 }

    fn get(self: @Self) -> i32
        return self.x

pub fn main() -> i32
    var p = P { x: 3 }
    let q = P { x: 1 }
    let r = p.bump(@q)
    return p.get() + r.x
""", 44),
    "generic": ("""\
struct Box<T>
    v: T

impl<T> Box<T>
    fn get(self: @Self) -> T
        return self.v

pub fn main() -> i32
    let b = Box<i32> { v: 3 }
    return b.get()
""", 3),
    # Two type params: `Self` is `Pair<K, V>`, both substituted.
    "generic2": ("""\
struct Pair<K, V>
    k: K
    v: V

impl<K, V> Pair<K, V>
    fn swap_v(self: @Self, v: V) -> Self
        return Pair<K, V> { k: self.k, v: v }

    fn sum(self:= Self) -> i32
        return self.k as i32 + self.v as i32

pub fn main() -> i32
    let a = Pair<u8, i64> { k: 3, v: 1 }
    return a.swap_v(40).sum()
""", 43),
    "trait": ("""\
trait Get
    fn get(self: @Self) -> i32

struct P
    x: i32

impl Get for P
    fn get(self: @Self) -> i32
        return self.x

pub fn main() -> i32
    let p = P { x: 3 }
    return p.get()
""", 3),
    # The ticket's second symptom: a Drop type, other methods in the impl. The
    # receiver moves into `burn` and is dropped once, there.
    "drop": ("""\
var drops: i32

struct T
    x: i32

impl Drop for T
    fn drop(self:&)
        drops = drops + 1

impl T
    fn peek(self: @T) -> i32
        return self.x

    fn burn(self:= Self) -> i32
        return self.x + 1

fn run() -> i32
    let t = T { x: 1 }
    return t.peek() + t.burn()

pub fn main() -> i32
    let r = run()
    return drops * 10 + r
""", 13),
}


@pytest.mark.parametrize("name", sorted(CASES))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_self_is_the_impls_type(compiler, name, tmp_path):
    program, want = CASES[name]
    assert _run(compiler, tmp_path, name, program) == want
