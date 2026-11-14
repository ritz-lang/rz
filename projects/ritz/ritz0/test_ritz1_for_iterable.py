"""AGAST #2375: `for x in iterable` that ritz1 can't lower must not skip the body.

    var g: [2]i32
    for v in g          # ritz0 ran the body, ritz1 emitted a zero-trip loop
    for v in h.a        # the same, with no diagnostic from ritz1 or clang

A global array and an array field now run.  Everything else emit_for_iterable
doesn't know is a located error, so an iterable that ritz0 accepts and ritz1
doesn't yet is a refusal rather than a loop that silently never happens.

A `for` walks its array in place and sees what its body writes, wherever the
array lives, with no hidden copy (#2387, LANGUAGE_SPEC §6.3).  Only an rvalue
gets a temporary, which nothing else can reach.  test_writes_in_the_body pins it.

Each program returns 0, or the number of the first check that failed.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

import ritz0_inproc
from test_borrow_param_ref_field import _compile, _run

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]

MAIN = "pub fn main() -> i32\n"


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    """_compile, by name.  The gate builds ritz1_selfhosted before pytest."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    """_run, by name."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


# Three distinct values.  Each differs from its neighbours in the low byte and
# above it, so neither a narrow nor a wide read passes by luck.
SCALARS = {
    "i8": ("-2", "-3", "-5"),
    "u8": ("200", "201", "202"),
    "i16": ("-300", "-301", "-302"),
    "u16": ("40000", "40001", "40002"),
    "i32": ("-70000", "-70001", "-70002"),
    "u32": ("3000000000", "3000000001", "3000000002"),
    "i64": ("-5000000000", "-5000000001", "-5000000002"),
    "u64": ("5000000000", "5000000001", "5000000002"),
    "f32": ("1.5", "2.5", "3.5"),
    "f64": ("1.5", "2.5", "3.5"),
    "bool": ("true", "false", "true"),
}


def _walk(it: str, ty: str, values: tuple, indent: str = "    ") -> str:
    """Check `it` yields exactly `values`, in order, as `ty`."""
    v0, v1, v2 = values
    body = (f"var i: i32 = 0\nfor v in {it}\n"
            f"    var w: {ty} = v\n"
            f"    if i == 0\n        if w != {v0}\n            return 1\n"
            f"    if i == 1\n        if w != {v1}\n            return 2\n"
            f"    if i == 2\n        if w != {v2}\n            return 3\n"
            f"    i = i + 1\nif i != 3\n    return 4\nreturn 0\n")
    return "".join(indent + line + "\n" for line in body.splitlines())


def _fill(place: str, values: tuple) -> str:
    return "".join(f"    {place}[{i}] = {v}\n" for i, v in enumerate(values))


def _struct(ty: str) -> str:
    # The canaries either side of the array show up a wrong offset or size.
    return f"struct H\n    lo: i64\n    a: [3]{ty}\n    hi: i64\n\n"


def _global(ty, vs):
    return f"var g: [3]{ty}\n\n" + MAIN + _fill("g", vs) + _walk("g", ty, vs)


def _field(ty, vs):
    return _struct(ty) + MAIN + "    var h: H\n" + _fill("h.a", vs) + _walk("h.a", ty, vs)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_a_global_array_runs(run_with, compiler, ty):
    assert run_with(compiler, f"g_{ty}", _global(ty, SCALARS[ty])) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_an_array_field_runs(run_with, compiler, ty):
    assert run_with(compiler, f"f_{ty}", _field(ty, SCALARS[ty])) == 0


V = ("7", "8", "9")
_H = _struct("i32")
_FILL = "    var h: H\n" + _fill("h.a", V)
_INNER = "struct O\n    k: i32\n    h: H\n\n"


def _callee(sig: str, it: str, call: str) -> str:
    return (_H + f"fn f({sig}) -> i32\n" + _walk(it, "i32", V) + "\n" + MAIN + _FILL
            + f"    return {call}\n")


# AGAST #2870: `mkp()[1].a`, an element of what a `*H` call returns, is a place.  The
# call runs once: 5 if not.  Element 1, so a stride but sizeof(H) shows up.
_CALLS = ("var hs: [2]H\nvar calls: i32 = 0\n\nfn mkp() -> *H\n    calls = calls + 1\n"
          "    return @hs[0]\n\nstruct K\n    n: i32\n\nimpl K\n    fn p(self: @K) -> *H\n"
          "        calls = calls + 1\n        return @hs[0]\n\n")


def _through_a_call(it: str, op: str = "") -> str:
    return (_H + _CALLS + "fn f() -> i32\n    var k: K\n" + _walk(op + it, "i32", V) + "\n" + MAIN
            + _fill("hs[1].a", V) + "    let r: i32 = f()\n    if r != 0\n        return r\n"
            "    if calls != 1\n        return 5\n    return 0\n")


# Every way emit_member_ptr reaches a field.
HOLDERS = {
    "by_value_param": _callee("h: H", "h.a", "f(h)"),
    "pointer_param": _callee("h: *H", "h.a", "f(@h)"),
    "reference_param": _callee("h: @H", "h.a", "f(@h)"),
    "mut_param": _callee("h:& H", "h.a", "f(@&h)"),
    "self": (_H + "impl H\n    fn f(self:&) -> i32\n" + _walk("self.a", "i32", V, " " * 8)
             + "\n" + MAIN + _FILL + "    return h.f()\n"),
    "nested": (_H + _INNER + MAIN + "    var o: O\n" + _fill("o.h.a", V)
               + _walk("o.h.a", "i32", V)),
    "global_struct": _H + "var gh: H\n\n" + MAIN + _fill("gh.a", V) + _walk("gh.a", "i32", V),
    "global_pointer": (_H + "var gp: *H = null\n\n" + MAIN + _FILL + "    gp = @h\n"
                       + _walk("gp.a", "i32", V)),
    "call_result": (_H + "fn mk() -> H\n" + _FILL + "    return h\n\n" + MAIN
                    + _walk("mk().a", "i32", V)),
    "array_element": (_H + MAIN + "    var hs: [2]H\n" + _fill("hs[1].a", V)
                      + _walk("hs[1].a", "i32", V)),
    "element_of_a_pointer_call": _through_a_call("mkp()[1].a"),
    "element_of_a_pointer_method": _through_a_call("k.p()[1].a"),
    "deref": _H + MAIN + _FILL + "    var p: *H = @h\n" + _walk("(*p).a", "i32", V),
    "alias": ("type T3 = [3]i32\nstruct H\n    a: T3\n\n" + MAIN + _FILL
              + _walk("h.a", "i32", V)),
    "alias_global": ("type T3 = [3]i32\nvar g: T3\n\n" + MAIN + _fill("g", V)
                     + _walk("g", "i32", V)),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(HOLDERS))
def test_every_holder_runs(run_with, compiler, name):
    assert run_with(compiler, name, HOLDERS[name]) == 0


_BOOLS = ("true", "false", "true")
_IF_V = ("    var t: i32 = 0\n    for v in {it}\n        if v\n            t = t + 1\n"
         "    if t != 2\n        return 1\n    return 0\n")


# The binding is a bool, not the integer it's kept in: a condition takes it.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name,program", [
    ("local", MAIN + "    var a: [3]bool = [true, false, true]\n" + _IF_V.format(it="a")),
    ("global", "var g: [3]bool\n\n" + MAIN + _fill("g", _BOOLS) + _IF_V.format(it="g")),
    ("field", _struct("bool") + MAIN + "    var h: H\n" + _fill("h.a", _BOOLS)
     + _IF_V.format(it="h.a")),
    ("pointer", "fn f(a: *[3]bool) -> i32\n" + _IF_V.format(it="a") + "\n" + MAIN
     + "    var a: [3]bool = [true, false, true]\n    return f(@a)\n"),
    ("row", MAIN + "    var m: [2][3]bool\n" + _fill("m[1]", _BOOLS) + _IF_V.format(it="m[1]")),
    ("literal", MAIN + _IF_V.format(it="[true, false, true]")),
], ids=["local", "global", "field", "pointer", "row", "literal"])
def test_a_bool_binding_is_a_condition(run_with, compiler, name, program):
    assert run_with(compiler, name, program) == 0


_S = "struct S\n    p: i16\n    q: i64\n    r: u8\n\n"
_SUM = ("    var t: i64 = 0\n    for e in {it}\n        t = t + e.q + (e.r as i64) + (e.p as i64)\n"
        "    if t != 66\n        return 1\n    return 0\n")


def _set(place: str) -> str:
    return "".join(f"    {place}[{i}].{f} = {v}\n"
                   for i, vals in enumerate([(1, 2, 3), (10, 20, 30)])
                   for f, v in zip("pqr", vals))


# A struct element is a whole `%S`, at the struct's stride, with its field names.
STRUCT_ELEMENTS = {
    "local": _S + MAIN + "    var a: [2]S\n" + _set("a") + _SUM.format(it="a"),
    "global": _S + "var a: [2]S\n\n" + MAIN + _set("a") + _SUM.format(it="a"),
    "field": (_S + "struct W\n    a: [2]S\n\n" + MAIN + "    var w: W\n" + _set("w.a")
              + _SUM.format(it="w.a")),
    "const": (_S + "const C: [2]S = [S { p: 1, q: 2, r: 3 }, S { p: 10, q: 20, r: 30 }]\n\n"
              + MAIN + _SUM.format(it="C")),
    "pointer": (_S + "fn f(a: *[2]S) -> i32\n" + _SUM.format(it="a") + "\n" + MAIN
                + "    var a: [2]S\n" + _set("a") + "    return f(@a)\n"),
    "row": _S + MAIN + "    var m: [2][2]S\n" + _set("m[1]") + _SUM.format(it="m[1]"),
    "literal": (_S + MAIN + _SUM.format(
        it="[S { p: 1, q: 2, r: 3 }, S { p: 10, q: 20, r: 30 }]")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(STRUCT_ELEMENTS))
def test_struct_elements_run(run_with, compiler, name):
    assert run_with(compiler, name, STRUCT_ELEMENTS[name]) == 0


# The binding is a `let`, so a write to its copy is refused rather than lost.
_LET = _S + "impl S\n    fn touch(self:&)\n        self.p = 1\n\nvar a: [2]S\n\n" + MAIN


def _is_let_error(comp, ll):
    assert comp.returncode != 0
    assert not ll.exists()
    assert "`let`" in comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_struct_binding_is_a_let(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "store", _LET + "    for e in a\n        e.p = 5\n    return 0\n")
    _is_let_error(comp, ll)


@pytest.mark.integration
def test_ritz0_refuses_a_mut_method_on_a_struct_binding(compile_with):
    comp, ll, _ = compile_with("ritz0", "method", _LET + "    for e in a\n        e.touch()\n    return 0\n")
    _is_let_error(comp, ll)


# AGAST #2389: a bare `self:&` receiver is a mutable borrow, as `self:& S` is.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_mut_method_on_a_struct_binding_is_refused(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "method", _LET + "    for e in a\n        e.touch()\n    return 0\n")
    _is_let_error(comp, ll)


# AGAST #2389: every element binding is a `let` in ritz0 (#1755), not just a
# struct's.  A store to it would only reach the loop's own copy.
_BINDING_STORES = {
    "scalar": ("var a: [2]i32\n\n", "x = 5"),
    "compound": ("var a: [2]u8\n\n", "x += 1"),
    "bool": ("var a: [2]bool\n\n", "x = true"),
    "pointer": ("var a: [2]*i32\n\n", "x = null"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(_BINDING_STORES))
def test_a_store_to_an_element_binding_is_refused(compile_with, compiler, kind):
    pre, store = _BINDING_STORES[kind]
    comp, ll, _ = compile_with(compiler, kind, pre + MAIN + "    for x in a\n        " + store + "\n    return 0\n")
    _is_let_error(comp, ll)
    # Located at the store (line 5), in ritz0's words.
    assert re.search(r":5:9: (error: )?cannot assign to `let` binding `x`; declare it `var`",
                     comp.stdout + comp.stderr), comp.stdout + comp.stderr


# The controls: a range variable is a `var`, and a pointer element's binding
# writes its pointee, not itself.
_BINDING_WRITES = {
    "range": "    var t: i32 = 0\n    for x in 0..3\n        x = 2\n        t = t + 1\n    return t - 1\n",
    # Through `p`: ritz1 can't store `@&n` into an element yet (#3036).
    "pointee": ("    var n: i32 = 1\n    var p: *i32 = @&n\n    var a: [2]*i32\n    a[0] = p\n    a[1] = p\n"
                "    for x in a\n        *x = *x + 1\n    return n - 3\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(_BINDING_WRITES))
def test_a_non_binding_write_in_a_for_runs(run_with, compiler, kind):
    assert run_with(compiler, kind, MAIN + _BINDING_WRITES[kind]) == 0


_DROPS = """\
struct D
    x: i32

var drops: i32 = 0

impl Drop for D
    fn drop(self:&)
        drops = drops + 1

"""


# The binding is a view of an element, not an owner: nothing drops per iteration.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("holder,pre,it", [
    ("global", "var a: [2]D\n\n", "a"),
    ("field", "struct W\n    a: [2]D\n\nvar w: W\n\n", "w.a"),
])
def test_a_move_only_element_is_not_dropped_by_the_loop(run_with, compiler, holder, pre, it):
    program = (_DROPS + pre + MAIN + "    var t: i32 = 0\n    for e in " + it + "\n"
               "        t = t + 1\n    if t != 2\n        return 1\n"
               "    if drops != 0\n        return 2\n    return 0\n")
    assert run_with(compiler, holder, program) == 0


_SUM_V = "    var t: i32 = 0\n    for v in {it}\n        t = t + v\n    return t\n"
_WRITES = ("    var t: i32 = 0\n    for v in {it}\n        {place}[2] = 50\n        t = t + v\n"
           "    return t\n")
_H3 = "struct H\n    k: i64\n    a: [3]i32\n    z: i64\n\n"
_SEED = (1, 2, 4)
_FILL3 = "    var h: H\n" + _fill("h.a", _SEED)
_GH = _H3 + "var gh: H\n\n"
_FILL_GH = _fill("gh.a", _SEED)


def _writes_in(sig: str, it: str, call: str, pre: str = _H3, fill: str = _FILL3) -> str:
    return (pre + f"fn f({sig}) -> i32\n" + _WRITES.format(it=it, place=it) + "\n" + MAIN + fill
            + f"    return {call}\n")


_POINTER_FN = "fn mkp() -> *H\n    return @gh\n\n"
_GA = "var ga: [3]i32\n\n"
_GR = "struct R\n    m: [2][3]i32\n\nvar gr: R\n\nfn mkp() -> *R\n    return @gr\n\n"
# LARB R17 (#3015): `.` reaches through a Box only by its `Deref` / `DerefMut`.
_BOX = ("struct Box<T>\n    ptr: *T\n\n"
        "impl<T> Deref for Box<T>\n    fn deref(self: @Box<T>) -> @T\n        @*self.ptr\n\n"
        "impl<T> DerefMut for Box<T>\n    fn deref_mut(self: @&Box<T>) -> @&T\n"
        "        @&*self.ptr\n\n")


# #2387.  1 + 2 + 50 where the loop walks the array, 1 + 2 + 4 where it walks a
# copy of it.
LIVE = {
    "local": MAIN + "    var a: [3]i32 = [1, 2, 4]\n" + _WRITES.format(it="a", place="a"),
    "by_value_param": _writes_in("a: [3]i32", "a", "f(a)", "", "    var a: [3]i32 = [1, 2, 4]\n"),
    "borrow_param": _writes_in("a:& [3]i32", "a", "f(@&a)", "", "    var a: [3]i32 = [1, 2, 4]\n"),
    "global": "var g: [3]i32\n\n" + MAIN + _fill("g", _SEED) + _WRITES.format(it="g", place="g"),
    "field": _H3 + MAIN + _FILL3 + _WRITES.format(it="h.a", place="h.a"),
    "field_of_a_by_value_param": _writes_in("h: H", "h.a", "f(h)"),
    "field_through_a_pointer": _writes_in("h: *H", "h.a", "f(@h)"),
    "field_through_a_reference": _writes_in("h: @&H", "h.a", "f(@&h)"),
    "field_through_a_borrow": _writes_in("h:& H", "h.a", "f(@&h)"),
    "self_field": (_H3 + "impl H\n    fn f(self:&) -> i32\n"
                   + "".join("    " + line + "\n"
                             for line in _WRITES.format(it="self.a", place="self.a").splitlines())
                   + "\n" + MAIN + _FILL3 + "    return h.f()\n"),
    "nested_field": (_H3 + "struct O\n    n: i32\n    h: H\n\n" + MAIN + "    var o: O\n"
                     + _fill("o.h.a", _SEED) + _WRITES.format(it="o.h.a", place="o.h.a")),
    "global_struct": _GH + MAIN + _FILL_GH + _WRITES.format(it="gh.a", place="gh.a"),
    "global_pointer": (_H3 + "var gp: *H = null\n\n" + MAIN + _FILL3 + "    gp = @h\n"
                       + _WRITES.format(it="gp.a", place="gp.a")),
    "pointer_field": (_H3 + "struct Q\n    n: i32\n    p: *H\n\n" + MAIN + _FILL3
                      + "    var q: Q\n    q.p = @h\n" + _WRITES.format(it="q.p.a", place="q.p.a")),
    "array_element": (_H3 + MAIN + "    var hs: [2]H\n" + _fill("hs[1].a", _SEED)
                      + _WRITES.format(it="hs[1].a", place="hs[1].a")),
    "pointer_element": (_H3 + "fn f(p: *H) -> i32\n" + _WRITES.format(it="p[1].a", place="p[1].a")
                        + "\n" + MAIN + "    var hs: [2]H\n" + _fill("hs[1].a", _SEED)
                        + "    return f(@hs[0])\n"),
    "deref_field": (_H3 + MAIN + _FILL3 + "    var p: *H = @h\n"
                    + _WRITES.format(it="(*p).a", place="h.a")),
    "alias": ("type T3 = [3]i32\nstruct H\n    a: T3\n\n" + MAIN + "    var h: H\n"
              + _fill("h.a", _SEED) + _WRITES.format(it="h.a", place="h.a")),
    "through_a_pointer_to_it": (_H3 + MAIN + _FILL3 + "    var p: *H = @h\n"
                                + _WRITES.format(it="h.a", place="p.a")),
    # AGAST #2410: what a `*[N]T`, a `*p` or a row names is walked in place.
    "deref": (MAIN + "    var a: [3]i32 = [1, 2, 4]\n    var p: *[3]i32 = @a\n"
              + _WRITES.format(it="*p", place="a")),
    "row": (MAIN + "    var m: [2][3]i32\n" + _fill("m[1]", _SEED)
            + _WRITES.format(it="m[1]", place="m[1]")),
    "global_row": ("var m: [2][3]i32\n\n" + MAIN + _fill("m[1]", _SEED)
                   + _WRITES.format(it="m[1]", place="m[1]")),
    "field_row": ("struct R\n    m: [2][3]i32\n\n" + MAIN + "    var r: R\n" + _fill("r.m[1]", _SEED)
                  + _WRITES.format(it="r.m[1]", place="r.m[1]")),
    # It was live before #2387, and stays so: what's given is the pointer.
    "pointer_to_an_array": ("fn f(a: *[3]i32, e: *i32) -> i32\n    var t: i32 = 0\n    for v in a\n"
                            "        *e = 50\n        t = t + v\n    return t\n\n" + MAIN
                            + "    var a: [3]i32 = [1, 2, 4]\n    return f(@a, @a[2])\n"),
    "mut_reference_to_an_array": ("fn f(a: @&[3]i32) -> i32\n" + _WRITES.format(it="a", place="a")
                                  + "\n" + MAIN + "    var a: [3]i32 = [1, 2, 4]\n    return f(@&a)\n"),
    # AGAST #2426: a place reached through a call, a cast or a Box.
    "field_of_a_pointer_call": (_GH + _POINTER_FN + MAIN + _FILL_GH
                                + _WRITES.format(it="mkp().a", place="gh.a")),
    "field_of_a_pointer_method": (_GH + "struct K\n    n: i32\n\nimpl K\n"
                                  "    fn p(self: @K) -> *H\n        return @gh\n\n" + MAIN
                                  + "    var k: K\n" + _FILL_GH
                                  + _WRITES.format(it="k.p().a", place="gh.a")),
    "field_of_a_generic_pointer_call": (_GH + "fn mkp<T>(a: T) -> *H\n    return @gh\n\n" + MAIN
                                        + _FILL_GH
                                        + _WRITES.format(it="mkp<i32>(1).a", place="gh.a")),
    "field_of_a_cast": (_H3 + MAIN + _FILL3 + "    var q: *u8 = @h as *u8\n"
                        + _WRITES.format(it="(q as *H).a", place="h.a")),
    "deref_of_a_call": (_GA + "fn mkp() -> *[3]i32\n    return @ga\n\n" + MAIN
                        + _fill("ga", _SEED) + _WRITES.format(it="*mkp()", place="ga")),
    "deref_of_a_global_pointer": (_GA + "var gp: *[3]i32 = null\n\n" + MAIN + _fill("ga", _SEED)
                                  + "    gp = @ga\n" + _WRITES.format(it="*gp", place="ga")),
    "row_of_a_pointer_call": (_GR + MAIN + _fill("gr.m[1]", _SEED)
                              + _WRITES.format(it="mkp().m[1]", place="gr.m[1]")),
    "tuple_element": (MAIN + "    var p: (i32, [3]i32) = (0, [1, 2, 4])\n"
                      + _WRITES.format(it="p.1", place="p.1")),
    "field_behind_a_box": (_BOX + _H3 + MAIN + _FILL3 + "    var b: Box<H>\n    b.ptr = @h\n"
                           + _WRITES.format(it="b.a", place="h.a")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LIVE))
def test_writes_in_the_body(run_with, compiler, name):
    assert run_with(compiler, name, LIVE[name]) == 53


# AGAST #2426: the call a place is reached through runs once, before the loop.
# 7 + 8 + 9, or 0 when it ran other than once.
_ONCE = "var calls: i32 = 0\n\n"
_ONCE_SUM = ("    var t: i32 = 0\n    for v in {it}\n        t = t + v\n"
             "    if calls != 1\n        return 0\n    return t\n")
ONCE = {
    "deref_of_a_call": (_ONCE + _GA + "fn mkp() -> *[3]i32\n    calls = calls + 1\n    return @ga\n\n"
                        + MAIN + _fill("ga", V) + _ONCE_SUM.format(it="*mkp()")),
    "row_of_a_pointer_call": (_ONCE + "struct R\n    m: [2][3]i32\n\nvar gr: R\n\n"
                              "fn mkp() -> *R\n    calls = calls + 1\n    return @gr\n\n" + MAIN
                              + _fill("gr.m[1]", V) + _ONCE_SUM.format(it="mkp().m[1]")),
    "row_of_a_pointer_method": (_ONCE + "struct R\n    m: [2][3]i32\n\nvar gr: R\n\nstruct K\n    n: i32\n\n"
                                "impl K\n    fn p(self: @K) -> *R\n        calls = calls + 1\n"
                                "        return @gr\n\n" + MAIN + "    var k: K\n" + _fill("gr.m[1]", V)
                                + _ONCE_SUM.format(it="k.p().m[1]")),
    "row_index": (_ONCE + "struct R\n    m: [2][3]i32\n\nfn mkp(r: *R) -> *R\n    return r\n\n"
                  "fn one() -> i64\n    calls = calls + 1\n    return 1\n\n" + MAIN
                  + "    var r: R\n" + _fill("r.m[1]", V) + _ONCE_SUM.format(it="mkp(@r).m[one()]")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ONCE))
def test_a_call_on_the_way_runs_once(run_with, compiler, name):
    assert run_with(compiler, name, ONCE[name]) == 24


# AGAST #2410: each was a located error on ritz1.  4, from 1 and 3.
_A = "    var a: [2]i32 = [1, 3]\n"
ARRAY_FAMILY = {
    "pointer_to_array": ("fn f(a: *[2]i32) -> i32\n" + _SUM_V.format(it="a") + "\n" + MAIN
                         + _A + "    return f(@a)\n"),
    "reference_to_array": ("fn f(a: @[2]i32) -> i32\n" + _SUM_V.format(it="a") + "\n" + MAIN
                           + _A + "    return f(@a)\n"),
    "local_pointer": MAIN + _A + "    var p: *[2]i32 = @a\n" + _SUM_V.format(it="p"),
    "deref": MAIN + _A + "    var p: *[2]i32 = @a\n" + _SUM_V.format(it="*p"),
    "literal": MAIN + _SUM_V.format(it="[1, 3]"),
    "row": MAIN + "    var m: [2][2]i32\n" + _fill("m[1]", (1, 3)) + _SUM_V.format(it="m[1]"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ARRAY_FAMILY))
def test_the_array_family_runs(run_with, compiler, name):
    assert run_with(compiler, name, ARRAY_FAMILY[name]) == 4


# The stride is the element's own, through a pointer and along a row.
TYPED = ("i8", "u16", "u32", "i64", "f32", "f64", "bool")
FAMILY_WALKS = {
    "pointer": lambda ty, vs: (f"fn f(a: *[3]{ty}) -> i32\n" + _walk("a", ty, vs) + "\n" + MAIN
                               + f"    var a: [3]{ty}\n" + _fill("a", vs) + "    return f(@a)\n"),
    "row": lambda ty, vs: (MAIN + f"    var m: [2][3]{ty}\n" + _fill("m[1]", vs)
                           + _walk("m[1]", ty, vs)),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(FAMILY_WALKS))
@pytest.mark.parametrize("ty", TYPED)
def test_the_array_family_reads_at_its_width(run_with, compiler, form, ty):
    assert run_with(compiler, f"{form}_{ty}", FAMILY_WALKS[form](ty, SCALARS[ty])) == 0


# A literal's element type is its first element's: f64 for `1.5`.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_float_literal_is_walked_as_floats(run_with, compiler):
    program = MAIN + _walk("[1.5, 2.5, 3.5]", "f64", SCALARS["f64"])
    assert run_with(compiler, "lit_f64", program) == 0


# Through a `**H`, which ritz0 only reads, so the write goes by way of `h`.
_LEVELS = "fn f(p: **H, h: *H) -> i32\n" + _WRITES.format(it="p.a", place="h.a")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_write_through_two_levels_is_seen(run_with, compiler):
    program = _H3 + _LEVELS + "\n" + MAIN + _FILL3 + "    var q: *H = @h\n    return f(@q, @h)\n"
    assert run_with(compiler, "levels", program) == 53


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_field_two_levels_down_is_live(run_with, compiler):
    program = (_H3 + "struct Q\n    n: i32\n    pp: **H\n\n" + MAIN + _FILL3
               + "    var q: *H = @h\n    var w: Q\n    w.pp = @q\n"
               + _WRITES.format(it="w.pp.a", place="h.a"))
    assert run_with(compiler, "levels_field", program) == 53


# `.` goes through every level (§5.4, #2398), so the loop and the store in its
# body both reach `h.a` through `**H` and `***H`.  ritz0 refused both.
_HOLD = "    var q: *H = @h\n    var r: **H = @q\n"
THROUGH_LEVELS = {"two": ("p: **H", "f(@q)"), "three": ("p: ***H", "f(@r)")}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("levels", sorted(THROUGH_LEVELS))
def test_a_write_through_the_walked_pointers_is_seen(run_with, compiler, levels):
    sig, call = THROUGH_LEVELS[levels]
    program = _writes_in(sig, "p.a", call, fill=_FILL3 + _HOLD)
    assert run_with(compiler, f"through_{levels}", program) == 53


# `@` of a tuple's element behind a pointer stays refused: only a `for`'s read
# reaches a tuple there.  Each of these is what ritz0 raised before a `for` was live.
_TUPLE_PTR = "fn f(p: *(i32, [3]i32)) -> i32\n"
NO_FURTHER = {
    "address_behind_a_pointer_to_a_tuple": (_TUPLE_PTR + "    let q: @i32 = @p.0\n    return *q\n\n"
                                            + MAIN + "    return 0\n"),
    "address_behind_a_reference_to_a_tuple": ("fn f(p: @(i32, [3]i32)) -> i32\n"
                                              "    let q: @i32 = @p.0\n    return *q\n\n"
                                              + MAIN + "    return 0\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NO_FURTHER))
def test_ritz0_a_for_leaves_a_store_and_an_address_alone(compile_with, name):
    comp, ll, _ = compile_with("ritz0", name, NO_FURTHER[name])
    assert comp.returncode != 0
    assert not ll.exists()
    out = comp.stdout + comp.stderr
    assert "Cannot access field on type" in out or "Unknown field" in out, out


@pytest.mark.integration
def test_ritz0_a_tuple_behind_a_pointer_is_live(run_with):
    program = ("fn f(p: *(i32, [3]i32), e: *i32) -> i32\n    var t: i32 = 0\n    for v in p.1\n"
               "        *e = 50\n        t = t + v\n    return t\n\n" + MAIN
               + "    var q: (i32, [3]i32) = (0, [1, 2, 4])\n    return f(@q, @q.1[2])\n")
    assert run_with("ritz0", "tuple_pointer", program) == 53


# LARB R17 (#3015): `@b.a` through a Box's `Deref` is legal now, and lends the
# boxed array itself: 4 is h.a[2].
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_address_through_a_box(run_with, compiler):
    program = (_BOX + _H3 + MAIN + _FILL3 + "    var b: Box<H>\n    b.ptr = @h\n"
               "    let q: @[3]i32 = @b.a\n    return q[2]\n")
    assert run_with(compiler, "address_through_a_box", program) == 4


# A Box's own field is its own, whatever the inner type has of that name (R17
# rule 4).  `b.ptr`
# is the pointer to the header, so the loop walks `s`: 1 + 2.
@pytest.mark.integration
def test_ritz0_a_boxs_own_field_comes_first(run_with):
    program = (_BOX + "struct V\n    ptr: *i32\n    len: i64\n\n" + MAIN
               + "    var a: [2]i32 = [1, 2]\n    var s = V { ptr: @a[0], len: 2 }\n"
               "    var b: Box<V>\n    b.ptr = @s\n    var t: i32 = 0\n    for x in b.ptr\n"
               "        t = t + x\n    return t\n")
    assert run_with("ritz0", "box_own", program) == 3


# AGAST #2426 / #3007: `b.ptr` is the Box's own `*H`, which no `for` walks, not
# `H`'s array `ptr` (LANGUAGE_SPEC, LARB R17: "`b.ptr` on a `Box<T>` is always
# the Box's own `ptr`, even when `T` has one").  Refused at the iterable on all
# three compilers; ritz0 raised a bare NotImplementedError traceback until #3007.
_REFUSED_ITERABLE = {"ritz0": "for loop iterable not supported",
                     "ritz1": "this `for` iterable is not supported",
                     "ritz1_selfhosted": "this `for` iterable is not supported"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_boxs_own_field_is_not_the_inner_one(compile_with, compiler):
    program = (_BOX + "struct H\n    k: i64\n    ptr: [3]i32\n\n" + MAIN + "    var h: H\n"
               "    var b: Box<H>\n    b.ptr = @h\n    var t: i32 = 0\n    for x in b.ptr\n"
               "        t = t + x\n    return t\n")
    comp, ll, _ = compile_with(compiler, "box_own_first", program)
    assert "Traceback" not in comp.stdout + comp.stderr
    _is_refused(comp, ll, _REFUSED_ITERABLE[compiler], program)


# Whoever writes.  What the loop walks is the array, not a name for it.
_POKE = "fn poke(a: *i32)\n    *a = 50\n\n"
OTHER_WRITERS = {
    "a_callee_through_a_pointer": (_H3 + _POKE + MAIN + _FILL3
                                   + "    var t: i32 = 0\n    for v in h.a\n"
                                   "        poke(@h.a[2])\n        t = t + v\n    return t\n"),
    "a_method": (_H3 + "impl H\n    fn set(self:&)\n        self.a[2] = 50\n\n" + MAIN + _FILL3
                 + "    var t: i32 = 0\n    for v in h.a\n        h.set()\n        t = t + v\n"
                 "    return t\n"),
    "a_whole_struct_store": (_H3 + MAIN + _FILL3 + "    var k: H = h\n    k.a[2] = 50\n"
                             "    var t: i32 = 0\n    for v in h.a\n        h = k\n"
                             "        t = t + v\n    return t\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(OTHER_WRITERS))
def test_any_writer_is_seen(run_with, compiler, name):
    assert run_with(compiler, name, OTHER_WRITERS[name]) == 53


# The binding is a copy of its element, taken before the body runs: a write to
# the element it holds shows on the next walk, not in the binding.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_binding_keeps_its_element(run_with, compiler):
    program = (_H3 + MAIN + _FILL3 + "    var t: i32 = 0\n    var i: i32 = 0\n    for v in h.a\n"
               "        h.a[i] = 0\n        t = t + v\n        i = i + 1\n"
               "    if t != 7\n        return 1\n    if h.a[2] != 0\n        return 2\n    return 0\n")
    assert run_with(compiler, "binding", program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_callers_struct_is_not_a_by_value_params(run_with, compiler):
    program = (_H3 + "fn f(h: H) -> i32\n" + _WRITES.format(it="h.a", place="h.a") + "\n" + MAIN
               + _FILL3 + "    let t: i32 = f(h)\n    if t != 53\n        return 1\n"
               "    if h.a[2] != 4\n        return 2\n    return 0\n")
    assert run_with(compiler, "by_value", program) == 0


# An rvalue has a temporary, and nothing else can reach it.  So `g` changing is
# no write to it: 1 + 2 + 4.
RVALUES = {
    "field_of_a_call": (_GH + "fn mk() -> H\n    return gh\n\n" + MAIN
                        + _FILL_GH + _WRITES.format(it="mk().a", place="gh.a")),
    "literal": (MAIN + "    var a: [3]i32 = [1, 2, 4]\n"
                + _WRITES.format(it="[a[0], a[1], a[2]]", place="a")),
}
# ritz1 has no array return value yet: it refuses `return g` (#2302, then #2997).
RVALUES_ON_RITZ0 = {
    "call": ("var g: [3]i32\n\nfn mk() -> [3]i32\n    return g\n\n" + MAIN + _fill("g", _SEED)
             + _WRITES.format(it="mk()", place="g")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RVALUES))
def test_an_rvalue_keeps_its_temporary(run_with, compiler, name):
    assert run_with(compiler, name, RVALUES[name]) == 7


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RVALUES_ON_RITZ0))
def test_ritz0_an_rvalue_keeps_its_temporary(run_with, name):
    assert run_with("ritz0", name, RVALUES_ON_RITZ0[name]) == 7


# What `h.a` is reached through is evaluated once.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_base_is_evaluated_once(run_with, compiler):
    program = (_H3 + "var calls: i32 = 0\n\nfn mk() -> H\n    calls = calls + 1\n    var h: H\n"
               + _fill("h.a", _SEED) + "    return h\n\n" + MAIN
               + "    var t: i32 = 0\n    for v in mk().a\n        t = t + v\n"
               "    if t != 7\n        return 1\n    if calls != 1\n        return 2\n    return 0\n")
    assert run_with(compiler, "once", program) == 0


_NEXT = "var calls: i32 = 0\n\nfn nxt() -> i64\n    calls = calls + 1\n    return 1\n\n"
_ONCE = ("    var t: i32 = 0\n    for v in {it}\n        t = t + v\n    if t != 7\n        return 1\n"
         "    if calls != 1\n        return 2\n    return 0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_index_on_the_way_is_evaluated_once(run_with, compiler):
    program = (_H3 + _NEXT + MAIN + "    var hs: [2]H\n" + _fill("hs[1].a", _SEED)
               + _ONCE.format(it="hs[nxt()].a"))
    assert run_with(compiler, "index_once", program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("name,program", [
    ("row", _NEXT + MAIN + "    var m: [2][3]i32\n" + _fill("m[1]", _SEED)
     + _ONCE.format(it="m[nxt()]")),
    ("pointer_call", _GH + "var calls: i32 = 0\n\nfn mkp() -> *H\n    calls = calls + 1\n"
     "    return @gh\n\n" + MAIN + _FILL_GH + _ONCE.format(it="mkp().a")),
], ids=["row", "pointer_call"])
def test_ritz0_is_evaluated_once(run_with, name, program):
    assert run_with("ritz0", name, program) == 0


# It's that array's writes the loop sees, not `p`'s.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_binding_doesnt_follow_a_repointed_base(run_with, compiler):
    program = (_H3 + MAIN + "    var h: H\n" + _fill("h.a", _SEED)
               + "    var k: H\n    var p: *H = @h\n    var t: i32 = 0\n    for v in p.a\n"
               "        p = @k\n        t = t + v\n    if t != 7\n        return 1\n    return 0\n")
    assert run_with(compiler, "repoint", program) == 0


# `module.G` is the global, not a load of it.  A name no value has, so it can't
# be reached the way `h.a` is.  ritz1 doesn't resolve this import.
@pytest.mark.integration
@pytest.mark.parametrize("name,decl,fill,it,write", [
    ("array", "pub var G: [3]i32\n", _fill("G", _SEED), "m.G", "G[2] = 50"),
    ("field", _H3 + "pub var G: H\n", _fill("G.a", _SEED), "m.G.a", "G.a[2] = 50"),
    ("row", "pub var G: [2][3]i32\n", _fill("G[1]", _SEED), "m.G[1]", "G[1][2] = 50"),
], ids=["array", "field", "row"])
def test_ritz0_a_module_global_is_live(tmp_path, name, decl, fill, it, write):
    (tmp_path / "m.ritz").write_text(decl)
    (tmp_path / "main.ritz").write_text(
        "import m\n\n" + MAIN + fill + f"    var t: i32 = 0\n    for v in {it}\n"
        f"        {write}\n        t = t + v\n    return t\n")
    lls = []
    for unit in ("main", "m"):
        ll = tmp_path / f"{unit}.ll"
        comp = ritz0_inproc.run_ritz0([str(tmp_path / f"{unit}.ritz"), "-o", str(ll)], cwd=tmp_path,
                                      env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)), timeout=300)
        assert comp.returncode == 0, comp.stdout + comp.stderr
        lls.append(str(ll))
    fast_link.clang(["clang", "-w", *lls, "-o", str(tmp_path / "main"), "-nostdlib"], check=True)
    assert subprocess.run([str(tmp_path / "main")], timeout=60).returncode == 53


# `k` is a value, so `k.a` is its field, however a global is named.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_field_is_not_a_global_of_its_name(run_with, compiler):
    program = (_H3 + "var a: [3]i32\n\n" + MAIN + _FILL3 + "    let k: H = h\n"
               "    var t: i32 = 0\n    for v in k.a\n        t = t + v\n    return t\n")
    assert run_with(compiler, "field_named_as_global", program) == 7


# A move out of a field goes on being one: the binding doesn't drop what left.
_MOVED = _DROPS + ("struct W\n    a: [2]D\n\n" + MAIN + "    var t: i32 = 0\n    if t == 0\n"
                   "        var w = W { a: [D { x: 1 }, D { x: 2 }] }\n        for e in w.a\n"
                   "            t = t + 1\n    if t != 2\n        return 1\n    return drops\n")


@pytest.mark.integration
def test_ritz0_a_moved_field_is_not_dropped_again(run_with):
    assert run_with("ritz0", "moved", _MOVED) == 0


# The same of a binding, which the checker has moved into the loop.
_MOVED_BINDING = ("struct L\n    d: *i32\n    n: i64\n\nvar drops: i32 = 0\n\nimpl Drop for L\n"
                  "    fn drop(self:&)\n        drops = drops + 1\n\n" + MAIN
                  + "    var a: [2]i32 = [1, 2]\n    var t: i32 = 0\n    if t == 0\n"
                  "        var l = L { d: @a[0], n: 2 }\n        for e in l\n"
                  "            t = t + e\n    if t != 3\n        return 1\n    return drops\n")


@pytest.mark.integration
def test_ritz0_a_moved_binding_is_not_dropped_again(run_with):
    assert run_with("ritz0", "moved_binding", _MOVED_BINDING) == 0


_CONTROL = ("    var t: i32 = 0\n    for v in {it}\n        if v == 2\n            continue\n"
            "        if v == 4\n            break\n        t = t + v\n"
            "    if t != 1\n        return 1\n    return 0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name,program", [
    ("global", "var g: [4]i32\n\n" + MAIN + _fill("g", (1, 2, 4, 8)) + _CONTROL.format(it="g")),
    ("field", "struct H\n    a: [4]i32\n\n" + MAIN + "    var h: H\n"
     + _fill("h.a", (1, 2, 4, 8)) + _CONTROL.format(it="h.a")),
], ids=["global", "field"])
def test_break_and_continue(run_with, compiler, name, program):
    assert run_with(compiler, name, program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_loop_nested_in_a_loop(run_with, compiler):
    program = ("var g: [2]i32\n\n" + _H3 + MAIN + "    var h: H\n" + _fill("h.a", _SEED)
               + _fill("g", (1, 10)) + "    var t: i32 = 0\n    for x in g\n        for y in h.a\n"
               "            t = t + x * y\n    if t != 77\n        return 1\n    return 0\n")
    assert run_with(compiler, "nested", program) == 0


# Nothing is copied, so nothing in the loop can grow the stack.  #1685: an alloca
# left in it would overrun at 4 KB a pass.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_loop_over_a_field_does_not_grow_the_stack(run_with, compiler):
    program = ("struct H\n    a: [1024]i32\n\n" + MAIN
               + "    var h: H\n    for k in 0..1024\n        h.a[k] = 0\n"
               "    h.a[1023] = 1\n    var t: i32 = 0\n    var i: i32 = 0\n"
               "    while i < 20000\n        for v in h.a\n            t = t + v\n"
               "        i = i + 1\n    if t != 20000\n        return 1\n    return 0\n")
    assert run_with(compiler, "stack", program) == 0


# 8 bytes a pass is enough, in 2,000,000 passes: what a `**H` param holds is read,
# not spilled to a slot in the loop.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_loop_through_two_levels_does_not_grow_the_stack(run_with, compiler):
    program = (_H3 + "fn f(p: **H) -> i32\n    var t: i32 = 0\n    var i: i32 = 0\n"
               "    while i < 2000000\n        for v in p.a\n            t = t + v\n"
               "        i = i + 1\n    if t != 14000000\n        return 1\n    return 0\n\n"
               + MAIN + _FILL3 + "    var q: *H = @h\n    return f(@q)\n")
    assert run_with(compiler, "stack_levels", program) == 0


# An `@T` param is the struct's address: nothing to spill to reach its field.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_loop_through_a_reference_does_not_grow_the_stack(run_with, compiler):
    program = (_H3 + "fn f(h: @H) -> i32\n    var t: i32 = 0\n    var i: i32 = 0\n"
               "    while i < 2000000\n        for v in h.a\n            t = t + v\n"
               "        i = i + 1\n    if t != 14000000\n        return 1\n    return 0\n\n"
               + MAIN + _FILL3 + "    return f(@h)\n")
    assert run_with(compiler, "stack_field_ref", program) == 0


# A `let` has no storage of its own on ritz0, and nothing can write to it, so its
# field is read, not spilled to a slot in the loop.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_loop_over_a_field_of_a_let_does_not_grow_the_stack(run_with, compiler):
    program = (_H3 + MAIN + _FILL3 + "    let k: H = h\n    var t: i32 = 0\n    var i: i32 = 0\n"
               "    while i < 2000000\n        for v in k.a\n            t = t + v\n"
               "        i = i + 1\n    if t != 14000000\n        return 1\n    return 0\n")
    assert run_with(compiler, "stack_let", program) == 0


# A reference is its own value: nothing to spill.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_loop_over_a_reference_does_not_grow_the_stack(run_with, compiler):
    program = ("fn f(a: @[3]i32) -> i32\n    var t: i32 = 0\n    var i: i32 = 0\n"
               "    while i < 2000000\n        for v in a\n            t = t + v\n"
               "        i = i + 1\n    if t != 14000000\n        return 1\n    return 0\n\n"
               + MAIN + "    var a: [3]i32 = [1, 2, 4]\n    return f(@a)\n")
    assert run_with(compiler, "stack_ref", program) == 0


# A literal's slot is static: a loop around the `for` doesn't make a new one a pass.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_literals_slot_does_not_grow_the_stack(run_with, compiler):
    program = (MAIN + "    var t: i32 = 0\n    var i: i32 = 0\n    while i < 2000000\n"
               "        for v in [1, 2, 4]\n            t = t + v\n        i = i + 1\n"
               "    if t != 14000000\n        return 1\n    return 0\n")
    assert run_with(compiler, "stack_lit", program) == 0


# A first-class load of a large array is what sends clang past 13 GB at -O2
# (AGAST #1730), and a copy of one was a second array on the stack.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_large_field_is_not_copied(compile_with, compiler):
    program = ("struct H\n    a: [100000]u8\n\n" + MAIN
               + "    var h: H\n    var t: i32 = 0\n    for v in h.a\n        t = t + 1\n"
               "    if t != 100000\n        return 1\n    return 0\n")
    comp, ll, _ = compile_with(compiler, "big", program)
    assert comp.returncode == 0, comp.stderr
    text = ll.read_text()
    assert "= load [" not in text
    assert "alloca [100000 x i8]" not in text
    assert "__ritz_sret_copy(" not in text


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_large_field_is_walked_to_its_end(run_with, compiler):
    program = ("struct H\n    a: [5000]u8\n\n" + MAIN
               + "    var h: H\n    for k in 0..5000\n        h.a[k] = 0\n"
               "    h.a[0] = 1\n    h.a[4999] = 2\n    var t: i32 = 0\n"
               "    for v in h.a\n        t = t + (v as i32)\n"
               "    if t != 3\n        return 1\n    return 0\n")
    assert run_with(compiler, "big_run", program) == 0


_ND = "    var t: i32 = 3\n    for r in {it}\n        t = t + 0\n    return t\n"
ND_MESSAGE = "iterating a multi-dimensional array is not supported in ritz1"

# AGAST #2410: `for r in m` over a `[N][M]T` binds each row, itself a `[M]T`.  A
# write to a later row shows when the loop gets there: 1 + 2 + 4 + 50 + 16 + 32.
_ROWS = ("    var t: i32 = 0\n    var k: i32 = 0\n    for r in {it}\n"
         "        {place}[1][0] = 50\n        t = t + r[0] + r[1] + r[2]\n        k = k + 1\n"
         "    if k != 2\n        return 1\n    return t\n")


def _rows(place: str) -> str:
    return _fill(f"{place}[0]", (1, 2, 4)) + _fill(f"{place}[1]", (8, 16, 32)) + _ROWS.format(
        it=place, place=place)


ROWS = {
    "local": MAIN + "    var m: [2][3]i32\n" + _rows("m"),
    "global": "var m: [2][3]i32\n\n" + MAIN + _rows("m"),
    "field": "struct N\n    m: [2][3]i32\n\n" + MAIN + "    var n: N\n" + _rows("n.m"),
    "alias_field": ("type G = [2][3]i32\nstruct N\n    m: G\n\n" + MAIN + "    var n: N\n"
                    + _rows("n.m")),
    "slice_of_3d": MAIN + "    var m: [2][2][3]i32\n" + _rows("m[1]"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_a_row_binding_is_an_array(run_with, compiler, name):
    assert run_with(compiler, name, ROWS[name]) == 105


# A row is a copy of its row, as an element is, taken before the body runs.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_row_binding_keeps_its_row(run_with, compiler):
    program = (MAIN + "    var m: [2][2]i64\n" + _fill("m[0]", (1, 2)) + _fill("m[1]", (4, 8))
               + "    var t: i64 = 0\n    for r in m\n        m[0][1] = 100\n"
               "        t = t + r[1]\n    return t as i32\n")
    assert run_with(compiler, "row_copy", program) == 10


# A bool row is `i1`s, as a `[M]bool` local is: a condition takes `r[2]`.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_bool_row_is_a_bool_array(run_with, compiler):
    program = (MAIN + "    var m: [2][3]bool\n" + _fill("m[0]", ("false", "false", "true"))
               + _fill("m[1]", ("true", "true", "false")) + "    var t: i32 = 0\n    for r in m\n"
               "        if r[2]\n            t = t + 1\n        if r[0]\n            t = t + 10\n"
               "    return t\n")
    assert run_with(compiler, "bool_rows", program) == 11


# Its slot is the row, not the i64 a bool element's binding is: a `[16 x i1]` row
# stored to an 8-byte slot would overrun it, whatever a run happens to show.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_bool_rows_slot_is_the_row(compile_with, compiler):
    program = (MAIN + "    var m: [2][16]bool\n    var t: i32 = 0\n    for r in m\n"
               "        if r[15]\n            t = t + 1\n    return t\n")
    comp, ll, _ = compile_with(compiler, "bool_row_slot", program)
    assert comp.returncode == 0, comp.stderr
    assert "alloca [16 x i1]" in ll.read_text()


# The row binding is a `let`, as an element is: a write to its copy is refused.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_row_binding_is_a_let(compile_with, compiler):
    program = MAIN + "    var m: [2][2]i32\n    for r in m\n        r[0] = 5\n    return 0\n"
    comp, ll, _ = compile_with(compiler, "row_let", program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert not ll.exists()
    assert "4:9:" in out and "cannot assign through `let` binding `r`; declare it `var`" in out, out


# A row of a 3-D array is itself 2-D, and stays refused (#1509).
NOT_LOWERED_ND = {
    "local": (MAIN + "    var m: [2][2][2]i32\n" + _ND.format(it="m")),
    "global": ("var m: [2][2][2]i32\n\n" + MAIN + _ND.format(it="m")),
}


def _is_refused(comp, ll, message, program):
    """Refused, at the iterable of the program's only `for`."""
    line, text = next((n, s) for n, s in enumerate(program.splitlines(), 1)
                      if s.lstrip().startswith("for "))
    col = text.index(" in ") + len(" in ") + 1
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert not ll.exists()
    assert f"main.ritz:{line}:{col}: {message}" in out, out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(NOT_LOWERED_ND))
def test_a_multi_dimensional_array_is_refused(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, NOT_LOWERED_ND[name])
    _is_refused(comp, ll, ND_MESSAGE, NOT_LOWERED_ND[name])


UNSUPPORTED = "this `for` iterable is not supported in ritz1"

_VEC = "import ritzlib.gvec\n\nstruct VH\n    v: Vec<i32>\n\n"
_NEW_VEC = "    var w: Vec<i32> = vec_new<i32>()\n"
_G = "var g: [2]i32\n\n"
_H2 = "struct H\n    n: i32\n    a: [2]i32\n\n"


# Each compiled to a loop that never ran.  ritz0 refuses these, and so does ritz1
# now.  What's lowered moves out: Vec, Span and StrView are in
# test_ritz1_for_header.py, `@a` / `@v` / `@h.a` in test_ritz1_for_addr_of.py
# (#2314, #2533), and the array family below (#2410).
BOTH_REFUSE = {
    "local_scalar": (MAIN + "    var n: i32 = 3\n" + _SUM_V.format(it="n")),
    "global_scalar": ("var n: i32\n\n" + MAIN + _SUM_V.format(it="n")),
    "scalar_field": (_H2 + MAIN + "    var h: H\n" + _SUM_V.format(it="h.n")),
    "unknown_name": (MAIN + _SUM_V.format(it="nope")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(BOTH_REFUSE))
def test_anything_else_is_a_located_error(compile_with, compiler, name):
    program = BOTH_REFUSE[name]
    comp, ll, _ = compile_with(compiler, name, program)
    _is_refused(comp, ll, UNSUPPORTED, program)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BOTH_REFUSE))
def test_ritz0_refuses_what_isnt_iterable(compile_with, name):
    comp, ll, _ = compile_with("ritz0", name, BOTH_REFUSE[name])
    assert comp.returncode != 0
    assert not ll.exists()


# `@v` over a local Vec is the form ritz1 had first.  test_ritz1_for_header.py runs it.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_the_vec_form_still_compiles(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "vec_ok", _VEC + MAIN + _NEW_VEC + _SUM_V.format(it="@w"))
    assert comp.returncode == 0, comp.stderr
    assert ll.exists()


_SHADOW = "var g: [2]i32\n\n" + MAIN + _fill("g", (1, 2))


# A local named like a global was read as the local by ritz1 and as the global
# by ritz0's `for` (#2386).  LARB R12 (AGAST #2407): it's an error at the local's
# name on all three, so no `for` can read either.  Line 6, after the two fills.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0"] + RITZ1S)
@pytest.mark.parametrize("local", ["var g: [2]i32 = [10, 20]", "var g: i32 = 0"])
def test_a_local_cant_take_a_global_arrays_name(compile_with, compiler, local):
    program = _SHADOW + f"    {local}\n" + _SUM_V.format(it="g")
    comp, ll, _ = compile_with(compiler, "shadow", program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert not ll.exists()
    sep = "" if compiler == "ritz0" else "error: "
    message = "a local can't take the name of a global: 'g' — rename the local"
    assert re.search(rf":6:9: {sep}{re.escape(message)}$", out, re.M), out[-1500:]
