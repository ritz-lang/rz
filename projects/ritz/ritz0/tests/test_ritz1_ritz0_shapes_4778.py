"""AGAST #4778: five shapes ritz0 accepts that ritz1 refused or miscompiled.

Found by #4692's tome and mausoleum slices, which the train refused under ritz1.

1. `struct Maker<T>` with a `make: fn() -> T` field: T was not substituted in
   the field's fn type, so `Maker<i64> { make: seven }` and
   `let f: fn() -> T = m.make` were refused; at every parameter of a
   `Conv<A, B>` too.
2. `h.item(0).next.get(0)`, a method on a field of a generic method's `@T`
   return: ritz1 called the method of the holder's Vec<Node> instance, a copy
   out of a move-only T, refused in gvec.
3. `g_conns.ids.get(0)` through a `*Conns` global: ritz1 instantiated the
   struct's *other* Vec field's `get`, as in 2; through a by-value global too.
4. `h.at(0).b = 9`, a field store through a generic method's `@&T` return:
   "unhandled EXPR_MEMBER in assignment".
5. SILENT: `return @page.data`, an inline array field through a pointer,
   returned as `[u8]`.  ritz1 exited 0 and returned the field's address, an
   i64, where the `%Span$u8` goes; clang refused the IR.  The `let s: [u8] =
   @page.data; return s` form was right.

ritz0 is the oracle.  Each program returns the value it computed, so a wrong
value shows as a wrong exit code; the shape 5 rows also check the span's
length and that it aliases the field.
"""

import pytest

from test_ritz1_for_header import COMPILERS, compile_with, run_with  # noqa: F401  (fixtures)

pytestmark = pytest.mark.batched

FN_FIELD = """\
struct Maker<T>
    make: fn() -> T

fn seven() -> i64
    7

fn build<T>(m: @Maker<T>) -> T
    let f: fn() -> T = m.make
    f()

pub fn main() -> i32
    let m: Maker<i64> = Maker<i64> { make: seven }
    build<i64>(@m) as i32
"""

# Each parameter of a multi-parameter struct, as the one above.
FN_FIELD_TWO_PARAMS = """\
struct Conv<A, B>
    conv: fn(A) -> B

fn twice(x: i32) -> i64
    (x as i64) * 2

fn run<A, B>(c: @Conv<A, B>, a: A) -> B
    let f: fn(A) -> B = c.conv
    f(a)

pub fn main() -> i32
    let c: Conv<i32, i64> = Conv<i32, i64> { conv: twice }
    run<i32, i64>(@c, 4) as i32
"""

# Node owns Vecs, so it is move-only: Vec<Node>.get (a copy out) is refused,
# which is what the wrong instance tripped on.
GENERIC_REF_RETURN_FIELD = """\
import ritzlib.gvec

struct Node
    name: Vec<u8>
    next: Vec<i64>

struct Holder<T>
    items: Vec<T>

impl<T> Holder<T>
    pub fn item(self: @Holder<T>, i: i64) -> @T
        @*(self.items.as_ptr() + i)

pub fn main() -> i32
    var h: Holder<Node> = Holder<Node> { items: vec_new<Node>() }
    var n: Vec<i64> = vec_new<i64>()
    n.push(4)
    n.push(6)
    h.items.push(Node { name: vec_new<u8>(), next: n })
    let r: i64 = h.item(0).next.get(1) + h.item(0).next.len()
    r as i32
"""

PTR_GLOBAL_FIELD = """\
import ritzlib.gvec

struct Conns
    names: Vec<Vec<u8>>
    ids: Vec<i64>

var g_conns: *Conns = null

fn first_id() -> i64
    g_conns.ids.get(1) + g_conns.ids.len()

pub fn main() -> i32
    var ids: Vec<i64> = vec_new<i64>()
    ids.push(5)
    ids.push(9)
    var c: Conns = Conns { names: vec_new<Vec<u8>>(), ids: ids }
    g_conns = @&c
    first_id() as i32
"""

# The same through a by-value global (a Drop one is refused: its Vecs are
# reached through pointers).
VALUE_GLOBAL_FIELD = """\
import ritzlib.gvec

struct Conns
    names: *Vec<Vec<u8>>
    ids: *Vec<i64>

var g_conns: Conns

fn first_id() -> i64
    g_conns.ids.get(1) + g_conns.ids.len()

pub fn main() -> i32
    var names: Vec<Vec<u8>> = vec_new<Vec<u8>>()
    var ids: Vec<i64> = vec_new<i64>()
    ids.push(5)
    ids.push(9)
    g_conns.names = @&names
    g_conns.ids = @&ids
    first_id() as i32
"""

GENERIC_MUT_REF_STORE = """\
import ritzlib.gvec

struct Pair
    a: i64
    b: i64

struct Holder<T>
    items: Vec<T>

impl<T> Holder<T>
    pub fn at(self: @&Holder<T>, i: i64) -> @&T
        @&*self.items.get_ptr(i)

pub fn main() -> i32
    var h: Holder<Pair> = Holder<Pair> { items: vec_new<Pair>() }
    h.items.push(Pair { a: 1, b: 2 })
    h.items.push(Pair { a: 3, b: 4 })
    h.at(1).b = 9
    (h.items.get(1).b * 10 + h.items.get(0).a) as i32
"""

# `tag` first puts the array off offset 0: a span taken at the struct shows.
_PAGE = """\
struct Page
    tag: i64
    data: [16]u8

fn page_bytes(page: {param}) -> [u8]
    return @page.data

pub fn main() -> i32
    var p: Page = Page {{ tag: 1, data: [0; 16] }}
    p.data[3] = 7
    let s: [u8] = page_bytes({arg})
    if s.len != 16
        return 100
    p.data[5] = 2
    (s[3] + s[5]) as i32
"""

PROGRAMS = {
    "fn_field_of_generic_struct": (FN_FIELD, 7),
    "fn_field_of_two_param_generic_struct": (FN_FIELD_TWO_PARAMS, 8),
    "method_on_field_of_generic_ref_return": (GENERIC_REF_RETURN_FIELD, 8),
    "method_on_field_through_ptr_global": (PTR_GLOBAL_FIELD, 11),
    "method_on_field_through_value_global": (VALUE_GLOBAL_FIELD, 11),
    "field_store_through_generic_mut_ref_return": (GENERIC_MUT_REF_STORE, 91),
    "return_array_field_as_span_ptr": (_PAGE.format(param="*Page", arg="@&p"), 9),
    "return_array_field_as_span_ref": (_PAGE.format(param="@Page", arg="@p"), 9),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_accepts_what_ritz0_accepts(run_with, name, compiler):
    program, want = PROGRAMS[name]
    assert run_with(compiler, name, program) == want
