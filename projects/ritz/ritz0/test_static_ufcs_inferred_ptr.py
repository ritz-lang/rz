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
"""

import pytest

import test_ritz1_for_header as for_header
import test_slice_value_local as slice_local

# #2451's fixtures: compile, link with gvec/span/string, run.
compile_with = for_header.compile_with
run_with = slice_local.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(STATICS))
def test_a_static_call_on_string(run_with, name, compiler):
    """`String.m(args)` with no impl method is `string_m(args)`."""
    body, want = STATICS[name]
    program = f"{STRING}{HELPERS}pub fn main() -> i32\n{body}"
    assert run_with(compiler, name, program) == want


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_static_call_with_no_fn_is_refused(compile_with, name, compiler):
    program = f"{STRING}{REFUSED[name]}"
    comp, ll, _ = compile_with(compiler, name, program)
    assert comp.returncode != 0, f"{compiler} accepted {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_user_impl_still_wins(run_with, compiler):
    """A user type's own static method is called, not a UFCS free fn."""
    program = (f"{STRING}struct W\n    n: i32\n\nimpl W\n    fn new() -> W\n        W {{ n: 11 }}\n\n"
               "fn w_new() -> W\n    W { n: 99 }\n\n"
               "pub fn main() -> i32\n    let w = W.new()\n    w.n\n")
    assert run_with(compiler, "user_impl", program) == 11


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_impl_method_on_string_beats_the_ufcs_fn(run_with, compiler):
    """`impl String { fn shout() }` is called over a free `string_shout()`."""
    program = (f"{STRING}impl String\n    fn shout() -> i32\n        22\n\n"
               "fn string_shout() -> i32\n    33\n\n"
               "pub fn main() -> i32\n    String.shout()\n")
    assert run_with(compiler, "impl_string", program) == 22


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

# The let's initialiser, each naming element 1 (E{3,4}).
INITS = {
    "generic_call": "vec_as_ptr<E>(@v) + 1",
    "generic_call_index": "vec_as_ptr<E>(@v) + i",
    "parenthesised": "(vec_as_ptr<E>(@v) + 1)",
    "chain": "vec_as_ptr<E>(@v) + 2 - 1",
    "plain_call": "mkp(@v) + 1",
    "local": "p + 1",
    "local_chain": "p + i + 1 - 1",
}

# How main uses `e`, and what ritz0 returns for element 1.
USES = {
    "address_of_field": ("    rd(@e.b) as i32\n", 4),
    "field": ("    e.b as i32\n", 4),
    "field_store": ("    e.b = 40\n    v[1].b as i32\n", 40),
    "next_element": ("    (*(e + 1)).a as i32\n", 5),
    "deref": ("    let c = *e\n    c.a as i32\n", 3),
}


# A scalar pointee too (#2598): `let e = <*T> ± k` is a `*T`.  w holds 5, 7,
# 9; each let names element 1.  It was an i64 with no pointee, so `*e = 30`
# stored 8 bytes (over element 2 for a `*i32`) and `e + 1` stepped one byte.
# `*i64` stores were right by luck (the let's i64 default is its width).
SCALAR_INITS = {"generic_call": "vec_as_ptr<{T}>(@w) + 1", "local": "q + 1",
                "chain": "q + 2 - 1", "local_chain": "q + i + 1 - 1"}

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
            "    var i: i64 = 1\n"
            f"    let e = {SCALAR_INITS[init].format(T=ty)}\n"
            f"{SCALAR_USES[use][0]}")
    return f"{PTR_HEADER}pub fn main() -> i32\n{body}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("use", sorted(SCALAR_USES))
@pytest.mark.parametrize("init", sorted(SCALAR_INITS))
@pytest.mark.parametrize("ty", SCALAR_TYPES)
def test_an_inferred_scalar_pointer(run_with, ty, init, use, compiler):
    """`let e = <*T> ± k` is a `*T`, exactly as if annotated."""
    got = run_with(compiler, f"{ty}_{init}_{use}", _scalar(ty, init, use))
    assert got == SCALAR_USES[use][1]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("use", sorted(USES))
@pytest.mark.parametrize("init", sorted(INITS))
def test_an_inferred_struct_pointer(run_with, init, use, compiler):
    """`let e = <*E> ± k` is a `*E`, exactly as if annotated."""
    body, want = USES[use]
    program = f"{PTR_HEADER}pub fn main() -> i32\n{PTR_SETUP}    let e = {INITS[init]}\n{body}"
    assert run_with(compiler, f"{init}_{use}", program) == want
