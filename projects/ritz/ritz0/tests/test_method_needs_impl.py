"""Method syntax reaches only impl methods (AGAST #3244, LANGUAGE_SPEC §9).

THE DEFECT

`a.cmp(b)` on a user `struct Foo` with only a free `fn foo_cmp(a: Foo, b: Foo)`
passed ritz0's type checker, which also tried `<lowercased type>_<method>`, and
then died in the emitter, which doesn't: `ValueError: No method 'cmp' found for
type 'Foo'`, a Python traceback with no location. ritz1 and ritz1_selfhosted
called an undeclared `@Foo_cmp(...)` and failed at link time.

THE RULE (Aaron, 2026-11-15)

`x.m(...)` on a user type resolves only to a method declared in an `impl` for
that type, or a trait impl. A free fn that happens to be called `foo_cmp` is not
a method. Otherwise all three compilers refuse it at the method name.

LARB R66 (#3496 ritz0, #3497 ritz1): that holds for ritzlib's types too. The
UFCS name tables that sent `s.len()` on a `String` to `string_len(@s)`, and
`v.m()` on a `Vec<T>`/`Span<T>`/`StrView` to `vec_m`/`span_m`/`strview_m`
(ritz0's ufcs.py; ritz1's ufcs_non_generic_prefix and ufcs_fn_def) are gone:
those methods are the types' `impl` blocks. The *_TABLE rows below are what
the tables used to dispatch and now refuse.
"""

import pytest

from ref_rules import no_method
from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration

FOO = """\
struct Foo
    x: i32
"""

ENUM = """\
enum Color
    Red
    Blue
"""

MAIN = """
pub fn main() -> i32
    let a = Foo { x: 1 }
    let b = Foo { x: 2 }
    a.^cmp(b)
"""

# name -> (program with `^` at the method name, message)
REFUSED = {
    # The ticket's program: a free `foo_cmp` is named in the hint.
    "free_foo_cmp": (
        FOO
        + """
fn foo_cmp(a: Foo, b: Foo) -> i32
    a.x - b.x
"""
        + MAIN,
        no_method("cmp", "Foo", "foo_cmp(a, b)"),
    ),
    # Nor is a free fn of the method's own name a method (ritz0's checker
    # tried that too).
    "free_cmp": (
        FOO
        + """
fn cmp(a: Foo, b: Foo) -> i32
    a.x - b.x
"""
        + MAIN,
        no_method("cmp", "Foo"),
    ),
    # An enum is a user type too: ritz1 called an undeclared `@Color_nope`
    # and failed at link time with no location (AGAST #1572).
    "enum_no_impl": (
        ENUM
        + """
pub fn main() -> i32
    let c = Color.Red
    c.^nope()
""",
        no_method("nope", "Color"),
    ),
}

# AGAST #1572, #3649: a generic instance has no `impl W$i32` to name in a
# hint. ritz1 and ritz1_selfhosted called an undeclared `@<Type>_nope` (a
# generic instance's methods are monomorphized per calling module, so one
# find_spec_impl_method misses is defined nowhere), and ritz0's emitter raised
# an unlocated ValueError. All three refuse it at the method name.
REFUSED |= {
    "generic_instance": (
        """\
struct W<T>
    x: T

impl<T> W<T>
    fn get(self: @W<T>) -> T
        self.x

pub fn main() -> i32
    let w = W<i32> { x: 1 }
    w.^nope()
""",
        no_method("nope", "W$i32"),
    ),
    # A UFCS-table generic (`vec_<m>$T`) with no `vec_nope`.
    "ufcs_table_generic": (
        """\
import ritzlib.gvec

pub fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.^nope()
""",
        no_method("nope", "Vec$i32"),
    ),
}

# AGAST #4262: a builtin-generic Option/Result whose ritzlib module isn't
# imported. ritz1 and ritz1_selfhosted called an undeclared
# `@Result$i32_i32_frob` and failed at link; ritz0 raised its own words.
# Refused at the method name whether or not ritzlib.option/result is imported.
OPTION_G = """\
struct G
    v: i32

fn mk() -> Option<G>
    Some(G { v: 7 })

pub fn main() -> i32
    let o = mk()
"""

RESULT_UNIMPORTED = """\
fn mk() -> Result<i32, i32>
    Ok(3)

pub fn main() -> i32
    let o = mk()
    o.^frob()
    0
"""

REFUSED |= {
    "option_builtin_unimported": (
        """\
fn mk() -> Option<i32>
    Some(3)

pub fn main() -> i32
    let o = mk()
    o.^frob()
    0
""",
        no_method("frob", "Option$i32"),
    ),
    # AGAST #4263: with a member access after it, ritz1 reported "cannot
    # emit: unhandled EXPR_MEMBER" at the outer expression instead.  `expect`
    # is no method of Option's: no emitter lowers it.
    "option_expect_then_member": (
        "import ritzlib.option\n\n" + OPTION_G + '    o.^expect("x").v\n',
        no_method("expect", "Option$G"),
    ),
    "option_frob_then_member": (
        "import ritzlib.option\n\n" + OPTION_G + "    o.^frob().v\n",
        no_method("frob", "Option$G"),
    ),
    "option_expect_then_member_unimported": (
        OPTION_G + '    o.^expect("x").v\n',
        no_method("expect", "Option$G"),
    ),
    # As a condition, ritz1's bool check said "if condition must be bool, and
    # ritz1 cannot tell that it is" before the method got its own error, once
    # `expect` left the carrier's payload methods (bool_kind.ritz).
    "option_expect_as_condition": (
        """\
fn mk() -> Option<bool>
    Some(true)

pub fn main() -> i32
    let o = mk()
    if o.^expect("x")
        return 1
    0
""",
        no_method("expect", "Option$bool"),
    ),
    # ...and, on an Option<i32>, "must be bool, got i32", typing `expect` as
    # the payload.
    "option_expect_i32_as_condition": (
        """\
fn mk() -> Option<i32>
    Some(1)

pub fn main() -> i32
    let o = mk()
    if o.^expect("x")
        return 1
    0
""",
        no_method("expect", "Option$i32"),
    ),
    "option_frob_as_condition": (
        """\
fn mk() -> Option<i32>
    Some(1)

pub fn main() -> i32
    let o = mk()
    if o.^frob()
        return 1
    0
""",
        no_method("frob", "Option$i32"),
    ),
}

# The deleted UFCS tables (R66, #3496/#3497): a free fn with a table prefix is
# no longer a method.  The generic arm was `vec_<m>$T`, so a free `vec_frob`
# beside a `Vec<u8>` receiver still is not `v.frob()`: AGAST #4537 moved the
# last vec_* free fns into `impl<T> Vec<T>`, tables and all.
REFUSED_TABLE = {
    # The non-generic table went by the type's name: String -> string_.
    "table_string_free_fn": (
        """\
struct String
    data: *u8
    len: i64
    cap: i64

fn string_len(s: @String) -> i64
    s.len

pub fn main() -> i32
    let s = String { data: null, len: 5, cap: 0 }
    s.^len() as i32
""",
        no_method("len", "String", "string_len(s)"),
    ),
    "table_vec_free_fn": (
        """\
import ritzlib.gvec

fn vec_frob(v: @Vec<u8>) -> i64
    v.len

pub fn main() -> i32
    var v: Vec<u8> = vec_new<u8>()
    v.^frob() as i32
""",
        no_method("frob", "Vec$u8"),
    ),
    # ritz1's lowercase `strview_<m>` fallback (#3240, folded into #3497).
    "table_strview_free_fn": (
        """\
fn strview_nope(s: StrView) -> i32
    s.len as i32

pub fn main() -> i32
    let s = "abc"
    s.^nope()
""",
        "no method `nope` on `StrView`",
    ),
    # ...and on a declared StrView, which ritz1 exempted from the refusal
    # while the fallback caught it, then called an undeclared `@StrView_nope`.
    "table_strview_declared_free_fn": (
        """\
fn strview_nope(s: StrView) -> i32
    s.len as i32

pub fn main() -> i32
    let s: StrView = "abc"
    s.^nope()
""",
        "no method `nope` on `StrView`",
    ),
}

# A StrView's methods are ritzlib's `impl StrView` and ritz0's emitter
# builtins (`len`, `as_bytes`): its emitter raised an unlocated ValueError for
# anything else (AGAST #3649). ritz1 named it `Span$u8` until AGAST #3697.
STRVIEW_REFUSED = {
    "strview": (
        """\
pub fn main() -> i32
    let s = "abc"
    s.^nope()
""",
        # Spelled out: StrView's impl is ritzlib's, so there is no hint.
        "no method `nope` on `StrView`",
    ),
}

# ...but a declared `Span<u8>` is one, and all three name it so. ritz0's
# emitter raised an unlocated ValueError for it (AGAST #3764).
SPAN_REFUSED = {
    "span_u8": (
        """\
pub fn main() -> i32
    let s: Span<u8> = "abc"
    s.^nope()
""",
        no_method("nope", "Span$u8"),
    ),
    # Nor is `as_bytes` a Span's: it is a StrView's builtin (AGAST #3699).
    "span_u8_as_bytes": (
        """\
pub fn main() -> i32
    let s: Span<u8> = "abc"
    s.^as_bytes()
""",
        no_method("as_bytes", "Span$u8"),
    ),
}

# name -> (program, exit status): what still dispatches.
DISPATCHED = {
    # The emitters' built-in `len` on a StrView, and on a generic `Vec`
    # instance with no `vec_len` in scope (AGAST #3649).
    "strview_len_builtin": (
        """\
pub fn main() -> i32
    let s = "abcd"
    s.len() as i32
""",
        4,
    ),
    "vec_len_builtin": (
        """\
struct Vec<T>
    data: *T
    len: i64
    cap: i64

pub fn main() -> i32
    let v = Vec<i32> { data: null, len: 3, cap: 0 }
    v.len() as i32
""",
        3,
    ),
    "impl_method": (
        FOO
        + """
impl Foo
    fn cmp(self: @Foo, b: Foo) -> i32
        self.x - b.x
"""
        + MAIN.replace("^", "").replace("a.cmp(b)", "a.cmp(b) + 10"),
        9,
    ),
    "trait_impl_method": (
        """\
trait Cmp
    fn cmp(self: @Self, b: Foo) -> i32

"""
        + FOO
        + """
impl Cmp for Foo
    fn cmp(self: @Foo, b: Foo) -> i32
        self.x - b.x
"""
        + MAIN.replace("^", "").replace("a.cmp(b)", "a.cmp(b) + 10"),
        9,
    ),
    # AGAST #1572: an enum's impl method, and a generic impl's at an instance.
    "enum_impl_method": (
        ENUM
        + """
impl Color
    fn code(self: @Color) -> i32
        match *self
            Red => 3
            Blue => 4

pub fn main() -> i32
    let c = Color.Blue
    c.code()
""",
        4,
    ),
    "generic_impl_method": (
        """\
struct W<T>
    x: T

impl<T> W<T>
    fn get(self: @W<T>) -> T
        self.x

pub fn main() -> i32
    let w = W<i32> { x: 6 }
    w.get()
""",
        6,
    ),
    # §7.7 rule 2: `w.get()` is the `Deref` target's method, not a missing one.
    "deref_target_method": (
        """\
struct Inner
    x: i32

impl Inner
    fn get(self: @Inner) -> i32
        self.x

struct Wrap
    inner: Inner

impl Deref for Wrap
    fn deref(self: @Wrap) -> @Inner
        @self.inner

pub fn main() -> i32
    let w = Wrap { inner: Inner { x: 7 } }
    w.get()
""",
        7,
    ),
    # AGAST #4263: the carrier's own `unwrap` still reaches the payload's field.
    "option_unwrap_then_member": (OPTION_G + "    o.unwrap().v\n", 7),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_method_syntax_needs_an_impl_method(tmp_path, compiler, name):
    program, message = REFUSED[name]
    _assert_refused(compiler, tmp_path, name, program, message)


# AGAST #4262. A two-argument instance is `Result$i32$i32` in all three: one
# `$` per argument (AGAST #4266).
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_unimported_result_method_it_lacks_is_refused(tmp_path, compiler):
    _assert_refused(compiler, tmp_path, "result_builtin_unimported", RESULT_UNIMPORTED,
                    no_method("frob", "Result$i32$i32"))


# AGAST #4266: a generic instance is named alike in every compiler's
# diagnostics: the base, then `$` and each argument's spelling, a nested
# instance by that same name (`W$V$i32$i64`), a pointer as `ptr_`.  ritz0 said
# `W$i32_i64` and `W$V_i32` (monomorph_core.mangle_generic_name's `_` join,
# still its linked names).  Not `W<i32, i64>`: ritz1 holds only the mangled
# name where it refuses, and a nested one does not split back into arguments.
W2 = """\
struct V<T>
    x: T

struct W<T, U>
    x: T
    y: U

struct W1<T>
    x: T

pub fn main() -> i32
"""

INSTANCE_NAMED = {
    "two_args": ("    let w = W<i32, i64> { x: 1, y: 2 }\n", "W$i32$i64"),
    "pointer_arg": ("    let w = W<*u8, i64> { x: null, y: 2 }\n", "W$ptr_u8$i64"),
    "nested_arg": ("    let w = W<V<i32>, i64> { x: V<i32> { x: 1 }, y: 2 }\n", "W$V$i32$i64"),
    "nested_one_arg": ("    let w = W1<V<i32>> { x: V<i32> { x: 1 } }\n", "W1$V$i32"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INSTANCE_NAMED))
def test_a_generic_instance_is_named_alike_in_every_compiler(tmp_path, compiler, name):
    binding, instance = INSTANCE_NAMED[name]
    program = W2 + binding + "    w.^nope()\n    0\n"
    _assert_refused(compiler, tmp_path, name, program, no_method("nope", instance))


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED_TABLE))
def test_a_ufcs_table_free_fn_is_not_a_method(tmp_path, compiler, name):
    program, message = REFUSED_TABLE[name]
    _assert_refused(compiler, tmp_path, name, program, message)


# What the tables carried now comes from the impls (#3240's pin): `v.parse_i64()`
# is `impl StrView`'s, and `b.push_bytes(..)` `impl<T> Vec<T>`'s (the method
# print-to-a-Vec sinks lower to). Built as a package so ritzlib links in.
IMPL_METHODS = """\
import ritzlib.strview
import ritzlib.option
import ritzlib.gvec

pub fn main() -> i32
    let v: StrView = "37"
    var r: Option<i64> = v.parse_i64()
    let bad: StrView = "3x"
    var q: Option<i64> = bad.parse_i64()
    var b: Vec<u8> = vec_new<u8>()
    if not b.push_bytes(c"abc", 3)
        return 1
    (r.unwrap_or(0) + q.unwrap_or(2) + b.len()) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_parse_i64_and_push_bytes_are_impl_methods(request, tmp_path, compiler):
    from test_ritz1_builtin_struct_shadow import _run_pkg
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    assert _run_pkg(compiler, tmp_path, "implm", IMPL_METHODS) == 42


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_strview_method_it_lacks_is_refused_as_strview(tmp_path, compiler):
    program, message = STRVIEW_REFUSED["strview"]
    _assert_refused(compiler, tmp_path, "strview", program, message)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SPAN_REFUSED))
def test_a_declared_span_u8_method_it_lacks_is_refused_as_span(tmp_path, compiler, name):
    program, message = SPAN_REFUSED[name]
    _assert_refused(compiler, tmp_path, name, program, message)


# `s.as_bytes()` is a builtin on a StrView, its `Span<u8>`, in all three (AGAST
# #3649).  ritz1 refused it on an unannotated `"..."`, a StrView in a `%Span$u8`
# slot; ritz0 raised an unlocated ValueError for the `.len` of a `Span<u8>` this
# module never declared (AGAST #3699).  4 + 4 + ('d' - 'a').
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_strview_as_bytes_is_its_span(tmp_path, compiler):
    program = """\
pub fn main() -> i32
    let s = "abcd"
    let b: Span<u8> = s.as_bytes()
    let c = s.as_bytes()
    (b.len + c.len) as i32 + (c[3] - c[0]) as i32
"""
    assert _run(compiler, tmp_path, "as_bytes", program) == 11


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(DISPATCHED))
def test_impl_methods_dispatch(tmp_path, compiler, name):
    program, want = DISPATCHED[name]
    assert _run(compiler, tmp_path, name, program) == want
