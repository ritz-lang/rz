"""AGAST #1629: a call's argument count and argument kinds are checked on ritz1.

    add(1, 2, 3)           # add takes 2:   "`add` called with 3 argument(s) but defined with 2"
    prints(p)              # p: *u8, prints takes a StrView
    g(s)                   # s a struct, g takes an i64

ritz0 refused each with a located error.  ritz1 and ritz1_selfhosted accepted
the extra or missing arguments silently, and turned a wrong-kinded argument into
IR that clang refused, pointing at the generated .ll rather than the source.

Now ritz1 says what ritz0 says, where ritz0 says it:

    arity        "`f` called with N argument(s) but defined with M", at the call
    kind         "argument N of `f` has the wrong type: ", at the argument

A method call is counted as its desugaring, `get(s, 1, 2)`: the receiver is
argument 1, as ritz0 counts it (#3319).  A static call has no receiver.

ritz0 spells the rest of a kind error in llvmlite's types (`%StrView != i8*`);
ritz1 names the parameter and what it got.  The kind rule is the part that is
sure to be wrong whatever the compiler makes of it: a pointer, float or `null`
into a by-value struct, and a struct value into an integer, float or bool.  The
coercions stay: a string literal into a StrView, a `:&` local passed on, a
struct place auto-borrowed by a `:&` param, an array into a Span.

ritz0 raises a Python IndexError for a method, static method or UFCS call of
the wrong arity until #3319 lands, so those rows run on ritz1 and
ritz1_selfhosted only.

A call through a fn pointer is counted against its `fn(..)` type: a local, a
param, or a nameless callee (`pick()(1, 2)`), which ritz0 accepted until #3333.
ritz0 calls a nameless one `<expression>`; ritz1 doesn't name it yet (#3348), so
its rows match the rest of the message.
`syscallN` takes N+1 arguments on every compiler (#3334).  An integer into a
single-field struct param is refused (LARB R47, spec §9.2): its rows are
test_int_arg_for_struct_param.py's.
"""

import pytest

import batching
import test_ritz1_for_header as for_header

pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]

HEADER = """\
import ritzlib.io
import ritzlib.sys
import ritzlib.gvec

struct S
    x: i32

struct T
    y: i64

struct W
    es: Vec<S>

impl S
    fn get(self: @S, i: i32) -> i32
        self.x + i
    fn make(x: i32) -> S
        S { x: x }

fn add(a: i32, b: i32) -> i32
    a + b

fn id<U>(a: U) -> U
    a

fn g(n: i64) -> i64
    n

fn fl(n: f64) -> f64
    n

fn byval(s: S) -> i32
    s.x

fn sv(v: StrView) -> i64
    v.len

fn lend(s:& S) -> i32
    s.x

fn pass_on(s:& S) -> i32
    byval(s)

fn inc(a: i32) -> i32
    a + 1

fn pick() -> fn(i32) -> i32
    inc

fn span_len(sp: Span<i32>) -> i64
    sp.len as i64

struct B
    pb: *[7]u8

struct C
    pi: *[7]i32

fn sv_of(pb: *[7]u8) -> i64
    sv(pb)

pub fn main() -> i32
    var s = S { x: 3 }
    var t = T { y: 4 }
    let ps: *S = @s
    let pt: *T = @t
    let p: *u8 = c"hi"
    let q: f64 = 1.5
    let i: i32 = 1
"""

ARITY = "`{f}` called with {n} argument(s) but defined with {m}"
NAMELESS = "` called with {n} argument(s) but defined with {m}"
WRONG = "argument {n} of `{f}` has the wrong type: "

# name -> (line with `@` at the column the error names, message[, extra]).
# Each line is main's next statement; main then returns 0.  With `extra`, it's
# the body of the fn `extra` declares (see _refused).
REFUSED = {
    "free_too_many": ("    return @add(1, 2, 3)", ARITY.format(f="add", n=3, m=2)),
    "free_too_few": ("    return @add(1)", ARITY.format(f="add", n=1, m=2)),
    # test_async_echo's shape (#1371): a format string and its values.
    "ritzlib_too_many": ('    @prints("x %d", i, i)', ARITY.format(f="prints", n=3, m=1)),
    "generic_too_many": ("    return @id<i32>(1, 2)", ARITY.format(f="id$i32", n=2, m=1)),
    # test_level18's shape (#1371): a `*u8` where prints takes a StrView.
    "pointer_into_strview": ("    prints(@p)", WRONG.format(n=1, f="prints")),
    # A `c"..."` literal says what to write instead (R62, AGAST #3440).
    "cstring_into_strview": ('    sv(@c"x")', 'a `c"..."` literal is a `*u8`, not a `StrView`: '
                             'write a plain `"..."` literal'),
    "other_pointer_into_struct": ("    byval(@pt)", WRONG.format(n=1, f="byval")),
    "null_into_struct": ("    byval(@null)", WRONG.format(n=1, f="byval")),
    "float_into_struct": ("    byval(@q)", WRONG.format(n=1, f="byval")),
    "struct_into_int": ("    g(@s)", WRONG.format(n=1, f="g")),
    "struct_into_float": ("    fl(@s)", WRONG.format(n=1, f="fl")),
    "second_argument": ("    add(1, @s)", WRONG.format(n=2, f="add")),
    # Through a fn pointer (#3333): counted and kinded as a direct call is.
    "fn_pointer_too_many": ("    let f: fn(i32) -> i32 = inc\n    return @f(1, 2)", ARITY.format(f="f", n=2, m=1)),
    "fn_pointer_too_few": ("    let f: fn(i32) -> i32 = inc\n    return @f()", ARITY.format(f="f", n=0, m=1)),
    "fn_pointer_struct_into_int": ("    let f: fn(i32) -> i32 = inc\n    return f(@s)", WRONG.format(n=1, f="f")),
    "fn_param_too_many": ("    return @h(1, 2)", ARITY.format(f="h", n=2, m=1),
                          "fn via(h: fn(i32) -> i32) -> i32\n"),
    "nameless_too_many": ("    return @pick()(1, 2)", NAMELESS.format(n=2, m=1)),
    # A `*[N]T` local or field of another element than u8 / i8 (AGAST #3349):
    # ritz1 passed the pointer's i64 where the %StrView goes, and clang refused.
    "array_pointer_wrong_elem_into_strview": ("    let pa: *[7]i32 = pi\n    return sv(@pa)", WRONG.format(n=1, f="sv"),
                                              "fn sv_i32(pi: *[7]i32) -> i64\n"),
    "array_pointer_field_wrong_elem_into_strview": ("    return sv(@c.pi)", WRONG.format(n=1, f="sv"),
                                                    "fn sv_field(c: C) -> i64\n"),
}

# ritz0 raises IndexError on these (#3319).
REFUSED_RITZ1 = {
    "method_too_many": ("    return @s.get(1, 2)", ARITY.format(f="get", n=3, m=2)),
    "method_too_few": ("    return @s.get()", ARITY.format(f="get", n=1, m=2)),
    "static_too_many": ("    let m = @S.make(1, 2)\n    return m.x", ARITY.format(f="make", n=2, m=1)),
    "ufcs_too_many": ("    var v: Vec<i32> = vec_new<i32>()\n    @v.push(1, 2)", ARITY.format(f="push", n=3, m=2)),
    "method_struct_into_int": ("    return s.get(@t)", WRONG.format(n=2, f="get")),
    "static_struct_into_int": ("    let m = S.make(@t)\n    return m.x", WRONG.format(n=1, f="make")),
    # The receiver is an element of a Vec field: the method is E's, not Vec's.
    "element_receiver_too_many": ("    var w: W = W { es: vec_new<S>() }\n    w.es.push(s)\n    return @w.es[0].get(1, 2)",
                                  ARITY.format(f="get", n=3, m=2)),
}


def _refused(compile_with, compiler, name, marked, message, extra=""):
    """`marked` is main's next lines, or with `extra`, the body of the fn
    `extra` declares last, before main."""
    lines = marked.splitlines()
    at = next(k for k, text in enumerate(lines) if "@" in text)
    column = 1 + lines[at].index("@")
    body = marked.replace("@", "", 1)
    tail = "\n" if "return" in body.splitlines()[-1] else "\n    return 0\n"
    if extra:
        fns, main = HEADER.split("pub fn main", 1)
        before = fns + extra
        program = before + body + tail + "\npub fn main" + main + "    return 0\n"
    else:
        before = HEADER
        program = HEADER + body + tail
    line = 1 + before.count("\n") + at
    batch = getattr(compile_with, "batch_compile", None)
    got = batching.refused(compiler, program, batch) if batch else None  # AGAST #2806
    if got is not None:
        out = got[0]
    else:
        comp, _, _ = compile_with(compiler, name, program)
        assert comp.returncode != 0, f"{compiler} took {name}"
        out = comp.stdout + comp.stderr
    assert message in out, out[-1000:]
    assert f"main.ritz:{line}:{column}:" in out, out[-1000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_call_that_does_not_fit_its_callee_is_refused(compile_with, name, compiler):
    _refused(compile_with, compiler, name, *REFUSED[name])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED_RITZ1))
def test_a_method_call_that_does_not_fit_is_refused(compile_with, name, compiler):
    _refused(compile_with, compiler, name, *REFUSED_RITZ1[name])


# The legal neighbours: each returns 7.  No ritzlib.io here: run_with links
# only the allocator's units.
LEGAL_HEADER = HEADER.replace("import ritzlib.io\n", "")
LEGAL = {
    "free": "    return add(3, 4)",
    "method": "    return s.get(4)",
    # `w.es[0].get(..)` is S's `get`, not the Vec's (test_ritz1_array_elem_field_type).
    "element_receiver": "    var w: W = W { es: vec_new<S>() }\n    w.es.push(s)\n    return w.es[0].get(4)",
    "static": "    let m = S.make(7)\n    return m.x",
    "ufcs": "    var v: Vec<i32> = vec_new<i32>()\n    v.push(7)\n    return v[0]",
    "generic": "    return id<i32>(7)",
    "literal_into_strview": '    return sv("abcdefg") as i32',
    "deref_into_struct": "    return byval(*ps) + 4",
    "place_borrowed": "    return lend(s) + 4",
    "lent_passed_on": "    return pass_on(s) + 4",
    "pointer_into_int": "    return (g(p as i64) - g(p as i64) + 7) as i32",
    "fn_pointer": "    let f: fn(i32) -> i32 = inc\n    return f(6)",
    # Coercions into a by-value struct param from something that isn't one.
    "vec_into_span": ("    var v: Vec<i32> = vec_new<i32>()\n" + "    v.push(1)\n" * 7
                      + "    return span_len(@v) as i32"),
    "array_into_span": "    var a: [7]i32\n    return span_len(@a) as i32",
    "array_into_strview": "    var b: [7]u8\n    return sv(b) as i32",
    "array_addr_into_strview": "    var b: [7]u8\n    return sv(@b) as i32",
    # ritz0 makes a StrView of a `*[N]u8` local, param or field (AGAST #3335):
    # ritz1 passed the pointer's i64 where the %StrView goes, and clang refused.
    "array_pointer_into_strview": "    var b: [7]u8\n    let pb: *[7]u8 = @b\n    return sv(pb) as i32",
    "array_pointer_param_into_strview": "    var b: [7]u8\n    return sv_of(@b) as i32",
    "array_pointer_field_into_strview": "    var b: [7]u8\n    let h = B { pb: @b }\n    return sv(h.pb) as i32",
}


# A `:&` local reads as the struct it borrows: into an i64 it's the wrong type
# as a struct value is.  Into a by-value struct of another type it's #3294's
# "another struct", said once in its words.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_lent_struct_into_an_int_is_refused(compile_with, compiler):
    _refused(compile_with, compiler, "lent_into_int", "    return g(@s)",
             WRONG.format(n=1, f="g"), extra="fn lent_g(s:& S) -> i64\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_lent_struct_of_another_type_is_another_struct(compile_with, compiler):
    _refused(compile_with, compiler, "lent_other", "    return byval(@t)",
             "parameter `s` is declared `S` but its argument is a `T`", extra="fn lent_t(t:& T) -> i32\n")
    comp, _, _ = compile_with(compiler, "lent_other_once", HEADER.split("pub fn main")[0]
                              + "fn lent_t(t:& T) -> i32\n    return byval(t)\n\npub fn main() -> i32\n    return 0\n")
    assert "has the wrong type" not in comp.stdout + comp.stderr


# A pointer to the param's own struct is ref_check's to refuse, in its words
# ("a reference or pointer doesn't fit a by-value slot"), said once.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_pointer_to_the_same_struct_is_not_a_wrong_type(compile_with, compiler):
    program = HEADER + "    return byval(ps)\n"
    comp, _, _ = compile_with(compiler, "same_struct_pointer", program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and "doesn't fit a by-value slot" in out, out[-1000:]
    assert "has the wrong type" not in out, out[-1000:]


# `syscallN(num, a1..aN)` takes N+1, counted like any call (#3334): ritz0's
# builtin used to pass whatever it got.  It is a ritzlib.sys fn now (#3397).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_syscall_is_counted(compile_with, compiler):
    _refused(compile_with, compiler, "syscall", "    @syscall2(39, 0, 0, 0)",
             "`syscall2` called with 4 argument(s) but defined with 3")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_a_call_that_fits_still_runs(run_with, name, compiler):
    assert run_with(compiler, name, LEGAL_HEADER + LEGAL[name] + "\n") == 7
