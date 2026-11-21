"""AGAST #2575: two shapes that stopped angelo's discovery.ritz on ritz1.

1. A static-style call on a builtin type with no `impl` method,
   `String.new()` / `String.from(x)`, is the UFCS free fn `string_new()` /
   `string_from(x)` with plain arguments (ritz0, #1321).  ritz1 had only the
   instance fallback (`s.push(c)` -> `string_push(@s, c)`) and refused the
   static one: "cannot determine receiver type for method call".

2. An un-annotated `let e = vec_as_ptr<E>(@v) + 1` lost its `*E`: `e.b` was
   "unhandled EXPR_MEMBER" and `@e.b` "cannot take address".  The annotated
   `let e: *E = ...` was right throughout.

ritz0 is the oracle: every expected status is what ritz0 returns.

The cases are rows of one table (test_table_rows.py, AGAST #3889), not a
parametrised matrix.  Each row keeps the id its parametrised test had, less
`test_` and the compiler: `test_an_inferred_scalar_pointer[i32-copy-store-ritz1]`
is `an_inferred_scalar_pointer[i32-copy-store]` on ritz1.  `test_every_row`
checks a chunk of rows per compiler, linked with gvec's allocator and
ritzlib/string as #2451's `run_with` did, and names each row that fails.
"""

import pytest

import test_ritz1_for_header as for_header
import test_slice_value_local as slice_local
import test_table_rows as table_rows
from test_table_rows import ALL, Refused, Row, Run, Whole

pytestmark = pytest.mark.integration

STRING = "import ritzlib.gvec\nimport ritzlib.string\n\n"

# name -> (main's body, ritz0's exit status).  Each result is then used as a
# String (a method on it, its length), so a let that lost its type shows.
STATICS = {
    "new": ("    var s = String.new()\n    s.push('a')\n    s.push('b')\n"
            "    s.len() as i32\n", 2),
    "from": ('    let t = String.from("xyz")\n    t.len() as i32\n', 3),
    "from_then_push": ('    var t = String.from("xy")\n    t.push_str("abc")\n'
                       "    t.len() as i32\n", 5),
    # Its Vec<u8> field: monomorph must know `t` is a String to instantiate
    # vec_push$u8 for `t.data.push`.
    "field_of_the_result": ('    var t = String.from("xy")\n    t.data.push(65)\n'
                            "    t.data.len as i32\n", 3),
    "from_i64": ("    let t = String.from_i64(4207)\n    t.len() as i32\n", 4),
    "from_cstr": ('    let t = String.from_cstr(c"hello")\n    t.len() as i32\n', 5),
    "annotated": ("    var s: String = String.new()\n    s.push('q')\n"
                  "    s.len() as i32\n", 1),
    "as_an_argument": ('    count(String.from("abcd"))\n', 4),
    "returned": ('    let t = make()\n    t.len() as i32\n', 6),
    "in_an_expression": ('    (String.from("ab").len() + String.from("cde").len()) as i32\n', 5),
    # A generic body is specialised, not walked: the rewrite runs on the clone.
    "in_a_generic_fn": ("    gen<i32>(7)\n", 9),
    # A global named like the type doesn't shadow it (a local does: REFUSED).
    "global_of_that_name": ('    let t = String.from("ab")\n    t.len() as i32 + String\n', 7),
}

HELPERS = (
    "var String: i32 = 5\n\n"
    "fn count(s: String) -> i32\n    s.len() as i32\n\n"
    'fn make() -> String\n    String.from("sixsix")\n\n'
    'fn gen<T>(x: T) -> i32\n    let s = String.from("ab")\n    x as i32 + s.len() as i32\n\n'
)


def _static(name):
    """`String.m(args)` with no impl method is `string_m(args)`."""
    body, want = STATICS[name]
    return Run(f"{STRING}{HELPERS}pub fn main() -> i32\n{body}", want)


# Neither compiler has these: no `string_with_capacity`, and `Vec` is generic
# (ritz0: "Unknown identifier: Vec").  Refused, never a silent call.
# A local or param named `String` is a value, and `String.new()` a method on it
# (ritz0: "No method 'new' found for type 'i32'"), not string_new().
REFUSED = {
    "no_such_fn": "pub fn main() -> i32\n    let s = String.with_capacity(8)\n    0\n",
    "generic_vec": "pub fn main() -> i32\n    var v: Vec<i32> = Vec.new()\n    0\n",
    "shadowed_by_a_local": "pub fn main() -> i32\n    let String: i32 = 5\n    let s = String.new()\n    0\n",
    "shadowed_by_a_param": ("fn f(String: i32) -> i32\n    let s = String.new()\n    0\n\n"
                            "pub fn main() -> i32\n    f(5)\n"),
}

# A user type's own static method is called, not a UFCS free fn.
USER_IMPL = (f"{STRING}struct W\n    n: i32\n\nimpl W\n    fn new() -> W\n        W {{ n: 11 }}\n\n"
             "fn w_new() -> W\n    W { n: 99 }\n\n"
             "pub fn main() -> i32\n    let w = W.new()\n    w.n\n")

# `impl String { fn shout() }` is called over a free `string_shout()`.
IMPL_STRING = (f"{STRING}impl String\n    fn shout() -> i32\n        22\n\n"
               "fn string_shout() -> i32\n    33\n\n"
               "pub fn main() -> i32\n    String.shout()\n")


PTR_HEADER = (
    "import ritzlib.gvec\n\n"
    "struct E\n    a: i64\n    b: i64\n\n"
    "fn rd(p: @i64) -> i64\n    *p\n\n"
    "fn mkp(v: *Vec<E>) -> *E\n    vec_as_ptr<E>(v)\n\n"
)

# v holds E{1,2}, E{3,4}, E{5,6}; `p: *E` is its first element and `i` is 1.
PTR_SETUP = (
    "    var v = vec_new<E>()\n"
    "    v.push(E { a: 1, b: 2 })\n    v.push(E { a: 3, b: 4 })\n    v.push(E { a: 5, b: 6 })\n"
    "    let p: *E = vec_as_ptr<E>(@v)\n"
    "    var i: i64 = 1\n"
)

# The let's initialiser -> the element it names, k.
INITS = {
    "generic_call": ("vec_as_ptr<E>(@v) + 1", 1),
    "generic_call_index": ("vec_as_ptr<E>(@v) + i", 1),
    "parenthesised": ("(vec_as_ptr<E>(@v) + 1)", 1),
    "chain": ("vec_as_ptr<E>(@v) + 2 - 1", 1),
    "plain_call": ("mkp(@v) + 1", 1),
    "local": ("p + 1", 1),
    "local_chain": ("p + i + 1 - 1", 1),
    # #2596: a plain copy of a `*E` local, and the `*E` field of an inferred
    # generic Vec, bare or offset.
    "copy": ("p", 0),
    "vec_field": ("v.data", 0),
    "vec_field_offset": ("v.data + 1", 1),
}

# How main uses `e` (element k is E{2k+1, 2k+2}), and what ritz0 returns.
USES = {
    "address_of_field": ("    rd(@e.b) as i32\n", lambda k: 2 * k + 2),
    "field": ("    e.b as i32\n", lambda k: 2 * k + 2),
    "field_store": ("    e.b = 40\n    v[{k}].b as i32\n", lambda k: 40),
    "next_element": ("    (*(e + 1)).a as i32\n", lambda k: 2 * k + 3),
    "deref": ("    let c = *e\n    c.a as i32\n", lambda k: 2 * k + 1),
}


# A scalar pointee too (#2598): `let e = <*T> ± k` is a `*T`.  w holds 5, 7,
# 9; each let names element 1.  It was an i64 with no pointee, so `*e = 30`
# stored 8 bytes (over element 2 for a `*i32`) and `e + 1` stepped one byte.
# `*i64` stores were right by luck (the let's i64 default is its width).
SCALAR_INITS = {"generic_call": "vec_as_ptr<{T}>(@w) + 1", "local": "q + 1",
                "chain": "q + 2 - 1", "local_chain": "q + i + 1 - 1",
                # #2596: a plain copy of a `*T` local, and a Vec's `*T` field.
                "copy": "q1", "vec_field": "w.data + 1"}

# How main uses `e`, and what ritz0 returns.
SCALAR_USES = {
    "store": ("    *e = 30\n    (*e + w[0] + w[2]) as i32\n", 44),
    "next_element": ("    *(e + 1) as i32\n", 9),
    "previous_element": ("    *(e - 1) as i32\n", 5),
}

SCALAR_TYPES = ["i64", "i32", "i16", "u8"]


def _scalar(ty: str, init: str, use: str) -> str:
    body = (f"    var w = vec_new<{ty}>()\n    w.push(5)\n    w.push(7)\n    w.push(9)\n"
            f"    let q: *{ty} = vec_as_ptr<{ty}>(@w)\n"
            f"    let q1: *{ty} = q + 1\n"
            "    var i: i64 = 1\n"
            f"    let e = {SCALAR_INITS[init].format(T=ty)}\n"
            f"{SCALAR_USES[use][0]}")
    return f"{PTR_HEADER}pub fn main() -> i32\n{body}"


def _struct(init, use):
    """`let e = <*E> ± k` (or a plain `*E` copy) is a `*E`, as if annotated."""
    init_expr, k = INITS[init]
    body, want = USES[use]
    return Run(f"{PTR_HEADER}pub fn main() -> i32\n{PTR_SETUP}    let e = {init_expr}\n"
               f"{body.format(k=k)}", want(k))


# ---- the rows: each id is its old test's, less `test_` and the compiler -------

# Rows importing ritzlib.string chunk apart from those importing only gvec: a row
# whose imports differ from its batch's is compiled alone as well (AGAST #2867).
ON_STRING = [
    *(Row(f"a_static_call_on_string[{name}]", ALL, _static(name)) for name in sorted(STATICS)),
    # Any refusal will do, located or not, as before: the compile just mustn't succeed.
    *(Row(f"a_static_call_with_no_fn_is_refused[{name}]", ALL,
          Refused(f"{STRING}{REFUSED[name]}", None, located=False)) for name in sorted(REFUSED)),
    Row("a_user_impl_still_wins", ALL, Run(USER_IMPL, 11)),
    Row("an_impl_method_on_string_beats_the_ufcs_fn", ALL,
        Refused(IMPL_STRING, Whole("`String` is declared in string.ritz: "
                                   "its `impl` must be there (§12.2)"), at=(4, 6))),
]
INFERRED = [
    # `let e = <*T> ± k` is a `*T`, exactly as if annotated.
    *(Row(f"an_inferred_scalar_pointer[{ty}-{init}-{use}]", ALL,
          Run(_scalar(ty, init, use), SCALAR_USES[use][1]))
      for ty in SCALAR_TYPES for init in sorted(SCALAR_INITS) for use in sorted(SCALAR_USES)),
    *(Row(f"an_inferred_struct_pointer[{init}-{use}]", ALL, _struct(init, use))
      for init in sorted(INITS) for use in sorted(USES)),
]
GROUPS = {"string": ON_STRING, "pointer": INFERRED}
TABLE = [*ON_STRING, *INFERRED]
CHUNKS = [(group, c, i) for group, rows in GROUPS.items() for c, i in table_rows.chunks(rows)]


@pytest.mark.parametrize("group,compiler,chunk", CHUNKS, ids=["-".join(map(str, c)) for c in CHUNKS])
def test_every_row(ritz1_bin, tmp_path, group, compiler, chunk):
    table_rows.assert_rows(compiler, table_rows.chunk(GROUPS[group], compiler, chunk),
                           build=for_header.batch_build(
                               ritz1_bin, lambda c: slice_local._string_objects(c, ritz1_bin)),
                           compile=for_header.batch_compile(ritz1_bin), work=tmp_path)
