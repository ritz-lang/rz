"""A type name that names nothing is refused, at the name (AGAST #3932).

`struct P` / `name: Nope` and `let q: Nope = 0` compiled under ritz0, which
laid `Nope` out as an opaque `{ i8 }`; ritz1 and ritz1_selfhosted emitted
`%Nope` IR clang refused with no source location ("use of undefined type
named 'Nope'", or "'%.3' defined with type 'i64' but expected '%Nope'").
The rule: every compiler says "unknown type `Nope`" where the name is
written, the words #3264 uses for an `impl` on one (ritz0/type_names.py,
ritz1/src/type_name_check.ritz).

Known names still compile and run: a generic's own parameter (a fn's, a
struct's, an impl's), `Self`, a type declared after its use, an imported one,
an enum, an alias, `StrView`, `usize`, a SIMD vector; and a slot ritz1's
parser fills with a name left over from an earlier type (`f: fn(i64) -> i64`
after `-> @&T`) is not judged by that name.
"""

import re

import pytest
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

MAIN = "\npub fn main() -> i32\n    3\n"

# `^` marks where the error lands: on the name.
REFUSED = {
    # The ticket's two programs.
    "field": "struct P\n    name: ^Nope\n",
    "let": "fn f() -> i32\n    let q: ^Nope = 0\n    0\n",
    # Every other place a name is written, on all three compilers.
    "field_ptr": "struct P\n    a: *^Nope\n",
    "field_array": "struct P\n    a: [2]^Nope\n",
    "var_ptr": "fn f() -> i32\n    var q: *^Nope = null\n    0\n",
    "let_in_if": "fn f(c: i32) -> i32\n    if c == 1\n        let q: *^Nope = null\n    0\n",
    "param": "fn f(x: ^Nope) -> i32\n    0\n",
    "param_ptr": "fn f(x: *^Nope) -> i32\n    0\n",
    "param_ref": "fn f(x: @^Nope) -> i32\n    0\n",
    "ret": "fn f() -> ^Nope\n    0\n",
    "ret_ptr": "fn f() -> *^Nope\n    null\n",
    "method_param": "struct S\n    a: i32\n\nimpl S\n    fn m(self: *S, x: *^Nope) -> i32\n        0\n",
    "global": "var g: *^Nope = null\n",
    "generic_fn": "fn f<T>(x: *T, y: *^Nope) -> i32\n    0\n",
    # A generic's parameter is in scope only in its own item.
    "param_out_of_scope": "struct B<T>\n    v: T\n\nfn f(x: *^T) -> i32\n    0\n",
    # A name written where ritz1's AST keeps no source spelling (AGAST #4021):
    # a generic argument (mangled `Option$Nope`), an enum payload (no enum
    # node), an unused alias's target and a cast's type.
    "generic_arg": "struct P\n    a: Option<^Nope>\n",
    "generic_arg_nested": "fn f(x: *Option<Option<*^Nope>>) -> i32\n    0\n",
    "generic_arg_let": "fn f() -> i32\n    var q: *Option<^Nope> = null\n    0\n",
    "enum_payload": "enum E\n    A(^Nope)\n    B\n",
    "enum_payload_n": "enum E\n    A(i32, *^Nope)\n    B\n",
    "alias_target": "type X = ^Nope\n",
    "alias_target_ptr": "type X = *^Nope\n",
    "cast": "fn f(p: *u8) -> i32\n    let q: *u8 = p as *^Nope as *u8\n    0\n",
    "cast_generic": "fn f(p: *u8) -> i32\n    let q: *u8 = p as *Option<^Nope> as *u8\n    0\n",
    # A generic's parameter is in scope in its own item only, there too.
    "generic_arg_out_of_scope": "struct B<T>\n    v: T\n\nfn f(x: *Option<^T>) -> i32\n    0\n",
    "cast_out_of_scope": "fn g<T>(x: *T) -> i32\n    0\n\nfn f(p: *u8) -> i32\n    let q: *u8 = p as *^T as *u8\n    0\n",
}

ROWS = [(c, site) for c in COMPILERS for site in sorted(REFUSED)]


@pytest.mark.parametrize("compiler,site", ROWS)
def test_an_unknown_type_name_is_refused(tmp_path, compiler, site):
    marked = REFUSED[site]
    name = re.search(r"\^(\w+)", marked).group(1)
    _assert_refused(compiler, tmp_path, site, marked + MAIN, f"unknown type `{name}`")


# One message, naming the type, and no IR: the ticket's clang failure was the
# second, unlocated, error.
@pytest.mark.parametrize("compiler", COMPILERS)
def test_one_located_message(tmp_path, compiler):
    src = (
        "struct P\n    name: Nope\n\nfn f() -> i32\n    let q: Nope = 0\n    0\n" + MAIN
    )
    comp, _, _ = _compile(compiler, tmp_path, "once", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert out.count("unknown type `Nope`") == 2, out
    assert ":2:11: " in out and ":5:12: " in out, out
    assert "undefined type" not in out and "expected '%Nope" not in out, out


KNOWN = (
    "import ritzlib.strview\n\n"
    "enum E\n    A\n    B\n\n"
    "type Id = i32\n\n"
    "struct Box<T>\n    v: T\n\n"
    "struct Holder\n    later: *Later\n    e: E\n    id: Id\n    s: StrView\n"
    "    n: usize\n    v: v4i32\n\n"
    "struct Later\n    x: i32\n\n"
    "impl<T> Box<T>\n    fn get(self: *Box<T>) -> T\n        self.v\n\n"
    # ritz1's parser leaves `T` in its state: a fn-typed field and a `-> *u8`
    # after it must not inherit it (the gate's first false positive).
    "    fn at(self: @&Box<T>) -> @&T\n        @&self.v\n\n"
    "struct Cb\n    f: fn(i64) -> i64\n\n"
    "fn raw(p: *u8) -> *u8\n    p\n\n"
    "impl Later\n    fn me(self: *Self) -> *Self\n        self\n\n"
    "fn first<T>(x: *T) -> T\n    let y: T = *x\n    y\n\n"
    # The positions AGAST #4021 judges, each with its item's own `T`: a
    # generic argument, a generic enum's payload, an alias's target, a cast.
    "enum Opt<T>\n    Has(*T)\n    Two(i32, Option<T>)\n    Not\n\n"
    "type BoxI = Box<i32>\n\ntype PL = *Later\n\n"
    "struct Wrap<T>\n    o: Option<*T>\n\n"
    "impl<T> Wrap<T>\n    fn raw(self: *Wrap<T>) -> *u8\n"
    "        let q: *Option<*T> = null\n        self as *Wrap<T> as *u8\n\n"
    "fn second<T>(x: *T) -> *u8\n    x as *Option<T> as *u8\n\n"
    # A comparison after a cast: `b` and `c` are values, not `Id<b, c>`.
    "fn two(x: bool, y: bool) -> i32\n    0\n\n"
    "fn cmp(a: i32, b: i32, c: i32, d: i32) -> i32\n    two(a as Id < b, c > d)\n\n"
    "pub fn main() -> i32\n    var l: Later = Later { x: 3 }\n"
    "    let p: *Later = l.me()\n    var b: Box<i32> = Box<i32> { v: p.x }\n"
    "    first<i32>(@b.v)\n"
)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_known_names_still_compile(tmp_path, compiler):
    assert _run(compiler, tmp_path, "known", KNOWN) == 3
