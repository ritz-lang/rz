"""AGAST #2375: `for x in iterable` that ritz1 can't lower must not skip the body.

    var g: [2]i32
    for v in g          # ritz0 ran the body, ritz1 emitted a zero-trip loop
    for v in h.a        # the same, with no diagnostic from ritz1 or clang

A global array and an array field now run.  Everything else emit_for_iterable
doesn't know is a located error, so an iterable that ritz0 accepts and ritz1
doesn't yet is a refusal rather than a loop that silently never happens.

A field is a copy and a global isn't: ritz0 reads `h.a` once through _emit_expr
into a temporary, and walks a bare name in place.  #2387 asks whether that's the
language; until then the three compilers agree, and test_writes_in_the_body pins
it.

Each program returns 0, or the number of the first check that failed.
"""

from pathlib import Path

import pytest

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
], ids=["local", "global", "field"])
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


# As any `let` on ritz1: let_check doesn't see a `self:&` receiver.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.xfail(strict=True, reason="AGAST #2389: a `self:&` method on a `let` compiles")
def test_a_mut_method_on_a_struct_binding_is_refused(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "method", _LET + "    for e in a\n        e.touch()\n    return 0\n")
    _is_let_error(comp, ll)


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


_WRITES = ("    var t: i32 = 0\n    for v in {it}\n        {place}[2] = 50\n        t = t + v\n"
           "    if t != {want}\n        return 1\n    return 0\n")
_H3 = "struct H\n    a: [3]i32\n\n"
_SEED = (1, 2, 4)


# #2387.  1 + 2 + 50 where the loop walks the array, 1 + 2 + 4 where it walks a
# copy of it.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name,program", [
    ("global_is_live", "var g: [3]i32\n\n" + MAIN + _fill("g", _SEED)
     + _WRITES.format(it="g", place="g", want=53)),
    ("field_is_a_copy", _H3 + MAIN + "    var h: H\n" + _fill("h.a", _SEED)
     + _WRITES.format(it="h.a", place="h.a", want=7)),
    ("field_through_a_pointer_is_a_copy",
     _H3 + "fn f(h: *H) -> i32\n" + _WRITES.format(it="h.a", place="h.a", want=7) + "\n"
     + MAIN + "    var h: H\n" + _fill("h.a", _SEED) + "    return f(@h)\n"),
], ids=["global", "field", "pointer"])
def test_writes_in_the_body(run_with, compiler, name, program):
    assert run_with(compiler, name, program) == 0


# The copy is taken once, and what `h.a` was reached through can change under it.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_base_is_evaluated_once(run_with, compiler):
    program = (_H3 + "var calls: i32 = 0\n\nfn mk() -> H\n    calls = calls + 1\n    var h: H\n"
               + _fill("h.a", _SEED) + "    return h\n\n" + MAIN
               + "    var t: i32 = 0\n    for v in mk().a\n        t = t + v\n"
               "    if t != 7\n        return 1\n    if calls != 1\n        return 2\n    return 0\n")
    assert run_with(compiler, "once", program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_binding_doesnt_follow_a_repointed_base(run_with, compiler):
    program = (_H3 + MAIN + "    var h: H\n" + _fill("h.a", _SEED)
               + "    var k: H\n    var p: *H = @h\n    var t: i32 = 0\n    for v in p.a\n"
               "        p = @k\n        t = t + v\n    if t != 7\n        return 1\n    return 0\n")
    assert run_with(compiler, "repoint", program) == 0


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


# #1685: the copy's alloca is static, so it's hoisted out of an enclosing loop.
# Had it not been, this overruns the stack at 4 KB a pass.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_the_copy_does_not_grow_the_stack(run_with, compiler):
    program = ("struct H\n    a: [1024]i32\n\n" + MAIN
               + "    var h: H\n    for k in 0..1024\n        h.a[k] = 0\n"
               "    h.a[1023] = 1\n    var t: i32 = 0\n    var i: i32 = 0\n"
               "    while i < 20000\n        for v in h.a\n            t = t + v\n"
               "        i = i + 1\n    if t != 20000\n        return 1\n    return 0\n")
    assert run_with(compiler, "stack", program) == 0


# A first-class load of a large array is what sends clang past 13 GB at -O2
# (AGAST #1730).  The copy goes from pointer to pointer, whatever the size.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_the_copy_is_not_a_first_class_load(compile_with, compiler):
    program = ("struct H\n    a: [100000]u8\n\n" + MAIN
               + "    var h: H\n    var t: i32 = 0\n    for v in h.a\n        t = t + 1\n"
               "    if t != 100000\n        return 1\n    return 0\n")
    comp, ll, _ = compile_with(compiler, "big", program)
    assert comp.returncode == 0, comp.stderr
    assert "= load [" not in ll.read_text()


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_large_array_copies_every_byte(run_with, compiler):
    program = ("struct H\n    a: [5000]u8\n\n" + MAIN
               + "    var h: H\n    for k in 0..5000\n        h.a[k] = 0\n"
               "    h.a[0] = 1\n    h.a[4999] = 2\n    var t: i32 = 0\n"
               "    for v in h.a\n        t = t + (v as i32)\n"
               "    if t != 3\n        return 1\n    return 0\n")
    assert run_with(compiler, "big_run", program) == 0


_SUM_V = "    var t: i32 = 0\n    for v in {it}\n        t = t + v\n    return t\n"
_ND = "    var t: i32 = 3\n    for r in {it}\n        t = t + 0\n    return t\n"
ND_MESSAGE = "iterating a multi-dimensional array is not supported in ritz1"

# Multi-dimensional iterables stay refused, as a local one is (#1509).
NOT_LOWERED_ND = {
    "local": (MAIN + "    var m: [2][2]i32\n" + _ND.format(it="m")),
    "global": ("var m: [2][2]i32\n\n" + MAIN + _ND.format(it="m")),
    "field": ("struct N\n    m: [2][2]i32\n\n" + MAIN + "    var n: N\n" + _ND.format(it="n.m")),
    "alias_field": ("type G = [2][2]i32\nstruct N\n    m: G\n\n" + MAIN + "    var n: N\n"
                    + _ND.format(it="n.m")),
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
_NEW_VEC = "    var v: Vec<i32> = vec_new<i32>()\n"
_A = "    var a: [2]i32 = [1, 3]\n"
_G = "var g: [2]i32\n\n"
_H2 = "struct H\n    n: i32\n    a: [2]i32\n\n"


# Each compiled to a loop that never ran.  ritz0 takes this first group, so each
# is a gap with a ticket; it refuses the second, and so does ritz1 now.
RITZ1_REFUSES = {
    "addr_of_local": (MAIN + _A + _SUM_V.format(it="@a")),
    "addr_of_global": (_G + MAIN + _SUM_V.format(it="@g")),
    "addr_of_field": (_H2 + MAIN + "    var h: H\n" + _SUM_V.format(it="@h.a")),
    "addr_of_mut_param": ("fn f(a:& [2]i32) -> i32\n" + _SUM_V.format(it="@a") + "\n" + MAIN
                          + _A + "    return f(@&a)\n"),
    "pointer_to_array": ("fn f(a: *[2]i32) -> i32\n" + _SUM_V.format(it="a") + "\n" + MAIN
                         + _A + "    return f(@a)\n"),
    "reference_to_array": ("fn f(a: @[2]i32) -> i32\n" + _SUM_V.format(it="a") + "\n" + MAIN
                           + _A + "    return f(@a)\n"),
    "deref": (MAIN + _A + "    var p: *[2]i32 = @a\n" + _SUM_V.format(it="*p")),
    "literal": (MAIN + _SUM_V.format(it="[1, 2]")),
    "row": (MAIN + "    var m: [2][2]i32\n" + _SUM_V.format(it="m[1]")),
    "vec": (_VEC + MAIN + _NEW_VEC + _SUM_V.format(it="v")),
    "vec_field": (_VEC + MAIN + "    var h: VH\n" + _SUM_V.format(it="h.v")),
    "addr_of_vec_field": (_VEC + MAIN + "    var h: VH\n" + _SUM_V.format(it="@h.v")),
    "vec_reference": (_VEC + "fn f(v: @Vec<i32>) -> i32\n" + _SUM_V.format(it="v") + "\n" + MAIN
                      + _NEW_VEC + "    return f(@v)\n"),
    "addr_of_vec_mut_param": (_VEC + "fn f(v:& Vec<i32>) -> i32\n" + _SUM_V.format(it="@v") + "\n"
                              + MAIN + _NEW_VEC + "    return f(@&v)\n"),
    "strview": (MAIN + "    let s: StrView = \"ab\"\n    var t: i32 = 0\n    for b in s\n"
                "        t = t + 1\n    return t\n"),
    "as_bytes": (MAIN + "    let s: StrView = \"ab\"\n    var t: i32 = 0\n    for b in s.as_bytes()\n"
                 "        t = t + 1\n    return t\n"),
}

BOTH_REFUSE = {
    "local_scalar": (MAIN + "    var n: i32 = 3\n" + _SUM_V.format(it="n")),
    "global_scalar": ("var n: i32\n\n" + MAIN + _SUM_V.format(it="n")),
    "scalar_field": (_H2 + MAIN + "    var h: H\n" + _SUM_V.format(it="h.n")),
    "unknown_name": (MAIN + _SUM_V.format(it="nope")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(RITZ1_REFUSES) + sorted(BOTH_REFUSE))
def test_anything_else_is_a_located_error(compile_with, compiler, name):
    program = {**RITZ1_REFUSES, **BOTH_REFUSE}[name]
    comp, ll, _ = compile_with(compiler, name, program)
    _is_refused(comp, ll, UNSUPPORTED, program)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BOTH_REFUSE))
def test_ritz0_refuses_what_isnt_iterable(compile_with, name):
    comp, ll, _ = compile_with("ritz0", name, BOTH_REFUSE[name])
    assert comp.returncode != 0
    assert not ll.exists()


# `@v` over a local Vec is the one Vec form ritz1 has, and it stays.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_the_vec_form_still_compiles(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "vec_ok", _VEC + MAIN + _NEW_VEC + _SUM_V.format(it="@v"))
    assert comp.returncode == 0, comp.stderr
    assert ll.exists()


_SHADOW = "var g: [2]i32\n\n" + MAIN + _fill("g", (1, 2))


# A local hides the global of the same name, so the global's array is never
# reached.  ritz0 looks at globals first (#2386).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_local_array_hides_a_global_one(run_with, compiler):
    program = _SHADOW + "    var g: [2]i32 = [10, 20]\n" + _SUM_V.format(it="g")
    assert run_with(compiler, "shadow", program) == 30


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_local_scalar_hides_a_global_array(compile_with, compiler):
    program = _SHADOW + "    var g: i32 = 0\n" + _SUM_V.format(it="g")
    comp, ll, _ = compile_with(compiler, "shadow_scalar", program)
    _is_refused(comp, ll, UNSUPPORTED, program)


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2386: ritz0 walks the global past the local")
def test_ritz0_local_array_hides_a_global_one(run_with):
    program = _SHADOW + "    var g: [2]i32 = [10, 20]\n" + _SUM_V.format(it="g")
    assert run_with("ritz0", "shadow", program) == 30
