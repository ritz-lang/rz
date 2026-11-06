"""AGAST #2388: `for` over a Vec, a Span or a StrView runs on ritz1.

    for x in v          # LANGUAGE_SPEC §6.3; ritz0 ran it, ritz1 refused it
    for w in self.ws    # prism
    for g in @run.gs    # angelo
    for b in s          # s: StrView
    for b in s.as_bytes()

All of them are a `{ data, len, .. }` header, and the loop walks `data[0..len]`.

The element comes from the header's `data` field, not from the mangled name.  The
name only ever told ritz1 about the integers: `@v` over a Vec<f64> read each
element as an i64, a Vec<f32> was invalid IR and a Vec<S> walked at 8 bytes.  An
element ritz1 can't name is refused, at the iterable.

The loop walks the header in place and reads it on every pass, because a `for`
sees what its body writes (#2387).  So a `push` is seen, and is safe when it moves
the buffer: test_a_push_that_moves_the_buffer.  ritz0 still reads a Vec by value
into a temporary, which #2387 will change; until then the rows where it does are
strict xfails, and it reads freed memory when the buffer moves.

The programs link the real allocator: a push is what's under test, and a single
compile can't link ritzlib.gvec's `realloc`.  Each returns 0, or the number of
the first check that failed, unless it says otherwise.
"""

import functools
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

import ritz0_inproc
from test_ritz1_for_iterable import (COMPILERS, MAIN, RITZ1S, SCALARS, SELFHOSTED_BIN, UNSUPPORTED,
                                     _is_refused)

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
GVEC = "import ritzlib.gvec\n\n"
ENV = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))

# What ritzlib.gvec's `realloc` needs, as build.py would link it.
UNITS = ("memory", "sys", "str", "fmt")


def _emit(compiler, ritz1_bin, src: Path, ll: Path):
    if compiler == "ritz0":
        return ritz0_inproc.run_ritz0([str(src), "-o", str(ll)], cwd=src.parent, env=ENV, timeout=300)
    binary = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}[compiler]
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=src.parent, env=ENV,
                          capture_output=True, text=True, timeout=300)


@functools.cache
def _objects(compiler, ritz1_bin) -> tuple:
    """The allocator's objects, compiled by `compiler`, once per process."""
    work = Path(tempfile.mkdtemp(prefix=f"for_header_{compiler}_"))
    objects = []
    for unit in UNITS:
        ll = work / f"{unit}.ll"
        comp = _emit(compiler, ritz1_bin, RITZ_ROOT / "ritzlib" / f"{unit}.ritz", ll)
        assert comp.returncode == 0, comp.stdout + comp.stderr
        obj = work / f"{unit}.o"
        subprocess.run(["clang", "-w", "-c", str(ll), "-o", str(obj)], check=True)
        objects.append(str(obj))
    return tuple(objects)


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    def go(compiler, name, program):
        work = tmp_path / f"{name}_{compiler}"
        work.mkdir()
        src, ll = work / "main.ritz", work / "main.ll"
        src.write_text(program)
        return _emit(compiler, ritz1_bin, src, ll), ll, work
    return go


@pytest.fixture
def run_with(ritz1_bin, compile_with):
    def go(compiler, name, program):
        comp, ll, work = compile_with(compiler, name, program)
        assert comp.returncode == 0 and ll.exists(), (
            f"{compiler} failed on {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
        exe = work / "main"
        cmd = ["clang", "-w", str(ll), *_objects(compiler, ritz1_bin), "-o", str(exe), "-nostdlib"]
        if compiler != "ritz0":
            cmd.insert(2, str(RITZ_START))
        link = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
        assert link.returncode == 0, f"{name} would not link:\n{link.stderr[-2000:]}"
        return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    return go


def _body(text: str, indent: str = "    ") -> str:
    return "".join(indent + line + "\n" for line in text.splitlines())


def _pushes(place: str, values) -> str:
    return "".join(f"    {place}.push({v})\n" for v in values)


def _new(ty: str, values, name: str = "v") -> str:
    return f"    var {name}: Vec<{ty}> = vec_new<{ty}>()\n" + _pushes(name, values)


def _new_through_locals(ty: str, values) -> str:
    """_new, for a literal ritz1 can't pass as it stands: `push(1.5)` to an f32 is #2412."""
    locals_ = "".join(f"    var c{i}: {ty} = {v}\n" for i, v in enumerate(values))
    return locals_ + _new(ty, [f"c{i}" for i in range(len(values))])


# Sums a `Vec<i32>`.  Seven, from 1, 2 and 4: a skipped or repeated element shows.
SUM = "var t: i32 = 0\nfor x in {it}\n    t = t + x\nif t != 7\n    return 1\nreturn 0\n"
SEED = (1, 2, 4)
FILL_V = _new("i32", SEED)
VH = "struct VH\n    k: i64\n    v: Vec<i32>\n    z: i64\n\n"
FILL_H = "    var h: VH\n    h.v = vec_new<i32>()\n" + _pushes("h.v", SEED)
OUTER = "struct O\n    n: i32\n    h: VH\n\n"
PH = "struct PH\n    k: i32\n    p: *Vec<i32>\n\n"


def _callee(sig: str, it: str, call: str, fill: str = FILL_V, pre: str = "") -> str:
    return (GVEC + pre + f"fn f({sig}) -> i32\n" + _body(SUM.format(it=it)) + "\n" + MAIN + fill
            + f"    return {call}\n")


def _in_main(it: str, fill: str, pre: str = "") -> str:
    return GVEC + pre + MAIN + fill + _body(SUM.format(it=it))


# Every way to hold a Vec<i32>.
HOLDERS = {
    "local": _in_main("v", FILL_V),
    "addr_of_local": _in_main("@v", FILL_V),
    "addr_mut_of_local": _in_main("@&v", FILL_V),
    "by_value_param": _callee("v: Vec<i32>", "v", "f(v)"),
    "reference_param": _callee("v: @Vec<i32>", "v", "f(@v)"),
    "mut_reference_param": _callee("v: @&Vec<i32>", "v", "f(@&v)"),
    "borrow_param": _callee("v:& Vec<i32>", "v", "f(@&v)"),
    "pointer_param": _callee("v: *Vec<i32>", "v", "f(@v)"),
    "field": _in_main("h.v", FILL_H, VH),
    "addr_of_field": _in_main("@h.v", FILL_H, VH),
    "addr_mut_of_field": _in_main("@&h.v", FILL_H, VH),
    "nested_field": _in_main("o.h.v", "    var o: O\n    o.h.v = vec_new<i32>()\n"
                             + _pushes("o.h.v", SEED), VH + OUTER),
    "field_through_pointer": _callee("h: *VH", "h.v", "f(@h)", FILL_H, VH),
    "field_through_reference": _callee("h: @VH", "h.v", "f(@h)", FILL_H, VH),
    "field_through_borrow": _callee("h:& VH", "h.v", "f(@&h)", FILL_H, VH),
    "addr_of_field_through_pointer": _callee("h: *VH", "@h.v", "f(@h)", FILL_H, VH),
    "self_field": (GVEC + VH + "impl VH\n    fn f(self:&) -> i32\n"
                   + _body(SUM.format(it="self.v"), " " * 8) + "\n" + MAIN + FILL_H
                   + "    return h.f()\n"),
    "addr_of_self_field": (GVEC + VH + "impl VH\n    fn f(self: @VH) -> i32\n"
                           + _body(SUM.format(it="@self.v"), " " * 8) + "\n" + MAIN + FILL_H
                           + "    return h.f()\n"),
    "pointer_field": _in_main("q.p", FILL_V + "    var q: PH\n    q.p = @v\n", PH),
    "global": _in_main("g", "    g = vec_new<i32>()\n" + "".join(
        f"    vec_push<i32>(@&g, {v})\n" for v in SEED), "var g: Vec<i32>\n\n"),
    "addr_of_global": _in_main("@g", "    g = vec_new<i32>()\n" + "".join(
        f"    vec_push<i32>(@&g, {v})\n" for v in SEED), "var g: Vec<i32>\n\n"),
    "global_pointer": _in_main("gp", FILL_V + "    gp = @v\n", "var gp: *Vec<i32> = null\n\n"),
    "global_struct_field": _in_main("gh.v", "    gh.v = vec_new<i32>()\n" + "".join(
        f"    vec_push<i32>(@&gh.v, {v})\n" for v in SEED), VH + "var gh: VH\n\n"),
    "call": _in_main("mk()", "", "fn mk() -> Vec<i32>\n" + FILL_V + "    return v\n\n"),
    # vec_push, as `v.push` doesn't link in a generic fn (#2412).
    "generic_call": _in_main("mk<i32>(1)", "", "fn mk<T>(a: T) -> Vec<T>\n"
                             "    var v: Vec<T> = vec_new<T>()\n    vec_push<T>(@&v, a)\n"
                             "    vec_push<T>(@&v, a + 1)\n    vec_push<T>(@&v, a + 3)\n"
                             "    return v\n\n"),
    "method_call": (GVEC + "struct K\n    n: i32\n\nimpl K\n    fn mk(self: @K) -> Vec<i32>\n"
                    + _body(FILL_V, "    ") + "        return v\n\n" + MAIN
                    + "    var k: K\n" + _body(SUM.format(it="k.mk()"))),
    "field_of_a_call": _in_main("mk().v", "", VH + "fn mk() -> VH\n" + FILL_H + "    return h\n\n"),
    "generic_fn": (GVEC + "fn f<T>(v: @Vec<T>) -> i32\n" + _body(SUM.format(it="v")) + "\n" + MAIN
                   + FILL_V + "    return f<i32>(@v)\n"),
    "unannotated_reference": _in_main("r", FILL_V + "    let r = @v\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(HOLDERS))
def test_every_holder_runs(run_with, compiler, name):
    assert run_with(compiler, name, HOLDERS[name]) == 0


# The example in §6.3, as the spec has it: an unannotated `let`, and nothing in it.
SPEC = (GVEC + "import ritzlib.io\n\nfn main() -> i32\n    let v = vec_new<i32>()\n"
        "    for item in v\n        print_int(item as i64)\n    0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_spec_example_compiles(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "spec", SPEC)
    assert comp.returncode == 0, comp.stdout + comp.stderr
    assert ll.exists()


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_unannotated_binding_holds_a_vec(run_with, compiler):
    program = (GVEC + MAIN + "    var v = vec_new<i32>()\n" + _pushes("v", SEED)
               + _body(SUM.format(it="v")))
    assert run_with(compiler, "unannotated", program) == 0


def _check(ty: str, values: tuple) -> str:
    v0, v1, v2 = values
    return (f"    var w: {ty} = x\n    if i == 0\n        if w != {v0}\n            return 1\n"
            f"    if i == 1\n        if w != {v1}\n            return 2\n"
            f"    if i == 2\n        if w != {v2}\n            return 3\n")


def _walk(it: str, n: int, check: str) -> str:
    return (f"var i: i32 = 0\nfor x in {it}\n" + check + f"    i = i + 1\nif i != {n}\n"
            "    return 9\nreturn 0\n")


NUMBERS = sorted(set(SCALARS) - {"bool"})
FORMS = ["v", "@v"]


# `@v` is here too: it read a float as an i64, or wrote IR that didn't assemble.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
@pytest.mark.parametrize("ty", NUMBERS)
def test_a_number_is_read_at_its_own_width(run_with, compiler, it, ty):
    vs = SCALARS[ty]
    program = GVEC + MAIN + _new_through_locals(ty, vs) + _body(_walk(it, 3, _check(ty, vs)))
    assert run_with(compiler, f"n_{ty}", program) == 0


# Field by field, each struct on the far side of 8 bytes from the old stride.
STRUCTS = {
    "two_bytes": ("struct S\n    a: u8\n    b: u8\n\n",
                  ("S { a: 1, b: 2 }", "S { a: 3, b: 4 }", "S { a: 5, b: 6 }"),
                  "    if x.a != ((i * 2 + 1) as u8)\n        return 1\n"
                  "    if x.b != ((i * 2 + 2) as u8)\n        return 2\n"),
    "eight_bytes": ("struct S\n    a: i32\n    b: i32\n\n",
                    ("S { a: 1, b: 2 }", "S { a: 3, b: 4 }", "S { a: 5, b: 6 }"),
                    "    if x.a != i * 2 + 1\n        return 1\n"
                    "    if x.b != i * 2 + 2\n        return 2\n"),
    "twelve_bytes": ("struct S\n    a: i32\n    b: i32\n    c: i32\n\n",
                     ("S { a: 1, b: 2, c: 3 }", "S { a: 4, b: 5, c: 6 }", "S { a: 7, b: 8, c: 9 }"),
                     "    if x.a != i * 3 + 1\n        return 1\n"
                     "    if x.c != i * 3 + 3\n        return 2\n"),
    "twenty_four_bytes": ("struct S\n    a: i64\n    b: i32\n    c: i64\n\n",
                          ("S { a: 1, b: 2, c: 3 }", "S { a: 4, b: 5, c: 6 }",
                           "S { a: 7, b: 8, c: 9 }"),
                          "    if x.a != ((i * 3 + 1) as i64)\n        return 1\n"
                          "    if x.b != i * 3 + 2\n        return 2\n"
                          "    if x.c != ((i * 3 + 3) as i64)\n        return 3\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
@pytest.mark.parametrize("name", sorted(STRUCTS))
def test_a_struct_is_walked_at_its_own_stride(run_with, compiler, it, name):
    pre, values, check = STRUCTS[name]
    program = GVEC + pre + MAIN + _new("S", values) + _body(_walk(it, 3, check))
    assert run_with(compiler, name, program) == 0


# The same, held in a field: the name is on the field, not on a local.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", ["h.v", "@h.v"])
def test_a_struct_field_vec_is_walked_at_its_stride(run_with, compiler, it):
    pre, values, check = STRUCTS["twenty_four_bytes"]
    program = (GVEC + pre + "struct H\n    k: i32\n    v: Vec<S>\n\n" + MAIN
               + "    var h: H\n    h.v = vec_new<S>()\n" + _pushes("h.v", values)
               + _body(_walk(it, 3, check)))
    assert run_with(compiler, "field", program) == 0


POINTERS = {
    # The neighbour is in the bytes a wide read would take, and `as i64` keeps them.
    "scalar": (GVEC + MAIN + "    var a: [3]i32 = [-70000, 5, 6]\n"
               "    var v: Vec<*i32> = vec_new<*i32>()\n    v.push(@a[0])\n    v.push(@a[1])\n"
               "    var t: i64 = 0\n    for x in {it}\n        t = t + (*x as i64)\n"
               "    if t != -69995\n        return 1\n    return 0\n"),
    "stride": (GVEC + MAIN + "    var a: [3]i32 = [1, 2, 4]\n"
               "    var v: Vec<*i32> = vec_new<*i32>()\n    v.push(@a[0])\n    var t: i32 = 0\n"
               "    for x in {it}\n        t = *(x + 2)\n    if t != 4\n        return 1\n"
               "    return 0\n"),
    "byte": (GVEC + MAIN + "    var a: [2]u8 = [200, 201]\n    var v: Vec<*u8> = vec_new<*u8>()\n"
             "    v.push(@a[0])\n    v.push(@a[1])\n    var t: i32 = 0\n    for x in {it}\n"
             "        var w: u8 = *x\n        if w != 200\n            if w != 201\n"
             "                return 1\n        t = t + 1\n    if t != 2\n        return 2\n"
             "    return 0\n"),
    "struct": (GVEC + "struct P\n    a: i64\n    b: i32\n\n" + MAIN + "    var p: P\n    p.b = 5\n"
               "    var v: Vec<*P> = vec_new<*P>()\n    v.push(@p)\n    var t: i32 = 0\n"
               "    for x in {it}\n        t = t + x.b\n    if t != 5\n        return 1\n"
               "    return 0\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
@pytest.mark.parametrize("name", sorted(POINTERS))
def test_a_pointer_element_knows_what_it_points_at(run_with, compiler, it, name):
    assert run_with(compiler, f"p_{name}", POINTERS[name].format(it=it)) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_vec_of_vecs(run_with, compiler):
    program = (GVEC + MAIN + _new("i32", (1, 2), "a") + _new("i32", (4,), "b")
               + "    var v: Vec<Vec<i32>> = vec_new<Vec<i32>>()\n    v.push(a)\n    v.push(b)\n"
               + _body("var t: i32 = 0\nfor r in v\n    for x in r\n        t = t + x\n"
                       "if t != 7\n    return 1\nreturn 0\n"))
    assert run_with(compiler, "vv", program) == 0


# No `push` for this one on ritz1 (#2412), so the header is built by hand.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
def test_a_bool_element_is_a_condition(run_with, compiler, it):
    program = (GVEC + MAIN + "    var a: [3]bool = [true, false, true]\n    var v: Vec<bool>\n"
               "    v.data = @a[0]\n    v.len = 3\n    v.cap = 3\n"
               + _body(f"var t: i32 = 0\nfor x in {it}\n    if x\n        t = t + 1\n"
                       "if t != 2\n    return 1\nreturn 0\n"))
    assert run_with(compiler, "bools", program) == 0


_DROPS = """\
struct D
    x: i32

var drops: i32 = 0

impl Drop for D
    fn drop(self:&)
        drops = drops + 1

"""


# The binding is a view of an element, as over an array.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_move_only_element_is_not_dropped_by_the_loop(run_with, compiler):
    program = (GVEC + _DROPS + MAIN + "    var v: Vec<D> = vec_new<D>()\n    var d: D\n"
               "    d.x = 5\n    v.push(d)\n"
               + _body("var t: i32 = 0\nfor e in v\n    t = t + e.x\nif t != 5\n    return 1\n"
                       "if drops != 0\n    return 2\nreturn 0\n"))
    assert run_with(compiler, "drops", program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_struct_binding_is_a_let(compile_with, compiler):
    pre, values, _ = STRUCTS["eight_bytes"]
    program = (GVEC + pre + MAIN + _new("S", values)
               + "    for x in v\n        x.a = 5\n    return 0\n")
    comp, ll, _ = compile_with(compiler, "store", program)
    assert comp.returncode != 0
    assert not ll.exists()
    assert "`let`" in comp.stdout + comp.stderr


# Trips, with `push` in the body while there's room: 3 was walking a copy, and 6
# sees the new `len`.
_TRIPS = "var n: i32 = 0\nfor x in {it}\n    if n < 3\n        {place}.push(x)\n    n = n + 1\nreturn n\n"
_GLOBAL_FILL = "".join(f"    vec_push<i32>(@&g, {v})\n" for v in SEED)
_TRIPS_G = ("var n: i32 = 0\nfor x in {it}\n    if n < 3\n        vec_push<i32>(@&g, x)\n"
            "    n = n + 1\nreturn n\n")
PUSHES = {
    "local": GVEC + MAIN + FILL_V + _body(_TRIPS.format(it="v", place="v")),
    "field": GVEC + VH + MAIN + FILL_H + _body(_TRIPS.format(it="h.v", place="h.v")),
    "field_through_pointer": (GVEC + VH + "fn f(h: *VH) -> i32\n"
                              + _body(_TRIPS.format(it="h.v", place="h.v")) + "\n" + MAIN + FILL_H
                              + "    return f(@h)\n"),
    "self_field": (GVEC + VH + "impl VH\n    fn f(self:&) -> i32\n"
                   + _body(_TRIPS.format(it="self.v", place="self.v"), " " * 8) + "\n" + MAIN
                   + FILL_H + "    return h.f()\n"),
    "global": GVEC + "var g: Vec<i32>\n\n" + MAIN + _GLOBAL_FILL + _body(_TRIPS_G.format(it="g")),
}
# ritz0 has these right already: what it's given is a pointer.
LIVE_ON_RITZ0 = {
    "addr_of_local": GVEC + MAIN + FILL_V + _body(_TRIPS.format(it="@v", place="v")),
    "addr_of_field": GVEC + VH + MAIN + FILL_H + _body(_TRIPS.format(it="@h.v", place="h.v")),
    "addr_of_global": (GVEC + "var g: Vec<i32>\n\n" + MAIN + _GLOBAL_FILL
                       + _body(_TRIPS_G.format(it="@g"))),
    "mut_reference_param": (GVEC + "fn f(v: @&Vec<i32>) -> i32\n"
                            + _body(_TRIPS.format(it="v", place="v")) + "\n" + MAIN + FILL_V
                            + "    return f(@&v)\n"),
    "pointer_field": (GVEC + PH + MAIN + FILL_V + "    var q: PH\n    q.p = @v\n"
                      + _body(_TRIPS.format(it="q.p", place="v"))),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(PUSHES) + sorted(LIVE_ON_RITZ0))
def test_a_push_in_the_body_is_seen(run_with, compiler, name):
    assert run_with(compiler, name, {**PUSHES, **LIVE_ON_RITZ0}[name]) == 6


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LIVE_ON_RITZ0))
def test_ritz0_a_push_through_a_pointer_is_seen(run_with, name):
    assert run_with("ritz0", name, LIVE_ON_RITZ0[name]) == 6


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PUSHES))
@pytest.mark.xfail(strict=True, reason="AGAST #2387: ritz0 walks a copy of the header")
def test_ritz0_a_push_in_the_body_is_seen(run_with, name):
    assert run_with("ritz0", name, PUSHES[name]) == 6


def _moves(it: str, place: str) -> str:
    """Eight 1s, and a push on the first pass big enough to move the buffer.

    Every element is checked, at the index it should be at: the 1s are read after
    the move, out of the new buffer, and a read of the old one finds what `free`
    left there.
    """
    return ("var n: i32 = 0\nvar t: i64 = 0\n"
            f"for x in {it}\n    if n == 0\n        for k in 0..100000\n"
            f"            {place}.push(2)\n"
            "    if n < 8\n        if x != 1\n            return 1\n"
            "    else\n        if x != 2\n            return 2\n"
            "    t = t + (x as i64)\n    n = n + 1\n"
            "if n != 100008\n    return 3\nif t != 200008\n    return 4\nreturn 0\n")


_EIGHT = "    var v: Vec<i32> = vec_new<i32>()\n    for k in 0..8\n        v.push(1)\n"
_EIGHT_H = "    var h: VH\n    h.v = vec_new<i32>()\n    for k in 0..8\n        h.v.push(1)\n"
MOVES = {
    "local": GVEC + MAIN + _EIGHT + _body(_moves("v", "v")),
    "addr_of_local": GVEC + MAIN + _EIGHT + _body(_moves("@v", "v")),
    "field": GVEC + VH + MAIN + _EIGHT_H + _body(_moves("h.v", "h.v")),
    "addr_of_field": GVEC + VH + MAIN + _EIGHT_H + _body(_moves("@h.v", "h.v")),
    "reference_param": (GVEC + "fn f(v: @&Vec<i32>) -> i32\n" + _body(_moves("v", "v")) + "\n" + MAIN
                        + _EIGHT + "    return f(@&v)\n"),
}


# #2387: safe, not refused.  ritz0 isn't run on the bare forms: it reads freed
# memory there, which is no value to pin.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(MOVES))
def test_a_push_that_moves_the_buffer(run_with, compiler, name):
    assert run_with(compiler, name, MOVES[name]) == 0


@pytest.mark.integration
@pytest.mark.parametrize("name", ["addr_of_local", "addr_of_field", "reference_param"])
def test_ritz0_a_push_through_a_pointer_that_moves_the_buffer(run_with, name):
    assert run_with("ritz0", name, MOVES[name]) == 0


# A struct element, wider than the binding's old i64 slot.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_struct_binding_survives_the_move(run_with, compiler):
    pre, values, _ = STRUCTS["twenty_four_bytes"]
    program = (GVEC + pre + MAIN + _new("S", values) + "    let w: S = S { a: 7, b: 8, c: 9 }\n"
               + _body("var t: i64 = 0\nvar n: i32 = 0\nfor x in v\n    if n == 0\n"
                       "        for k in 0..100000\n            v.push(w)\n"
                       "    if n == 0\n        if x.c != 3\n            return 1\n"
                       "    n = n + 1\nif n != 100003\n    return 2\nreturn 0\n"))
    assert run_with(compiler, "moved_s", program) == 0


# The elements were always shared.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
def test_an_element_write_in_the_body_is_seen(run_with, compiler, it):
    program = (GVEC + MAIN + FILL_V + _body(f"var t: i32 = 0\nfor x in {it}\n    v.set(2, 50)\n"
                                            "    t = t + x\nreturn t\n"))
    assert run_with(compiler, "set", program) == 53


_ADJUST = (GVEC + MAIN + FILL_V + "    var w: Vec<i32> = vec_new<i32>()\n    w.push(1)\n"
           "    var n: i32 = 0\n    for x in v\n        n = n + 1\n{body}    return n\n")


# #2387: anything that changes the header, not only a push.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name,body,trips", [
    ("pop", "        v.pop()\n", 2),
    ("clear", "        v.clear()\n", 1),
    ("assign", "        v = w\n", 1),
    ("drop", "        vec_drop<i32>(@&v)\n", 1),
], ids=["pop", "clear", "assign", "drop"])
def test_a_shorter_header_ends_the_loop(run_with, compiler, name, body, trips):
    assert run_with(compiler, name, _ADJUST.format(body=body)) == trips


# A view is the same: a `for` over a StrView sees it reassigned.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_view_written_in_the_body_is_seen(run_with, compiler):
    program = (MAIN + "    var s: StrView = \"abc\"\n    let e: StrView = \"a\"\n    var n: i32 = 0\n"
               "    for b in s\n        s = e\n        n = n + 1\n    return n\n")
    assert run_with(compiler, "view", program) == 1


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_call_is_evaluated_once(run_with, compiler):
    program = (GVEC + "var calls: i32 = 0\n\nfn mk() -> Vec<i32>\n    calls = calls + 1\n" + FILL_V
               + "    return v\n\n" + MAIN
               + _body("var t: i32 = 0\nfor x in mk()\n    t = t + x\nif t != 7\n    return 1\n"
                       "if calls != 1\n    return 2\nreturn 0\n"))
    assert run_with(compiler, "once", program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_fields_base_is_evaluated_once(run_with, compiler):
    program = (GVEC + VH + "var calls: i32 = 0\n\nfn mk() -> VH\n    calls = calls + 1\n" + FILL_H
               + "    return h\n\n" + MAIN
               + _body("var t: i32 = 0\nfor x in mk().v\n    t = t + x\nif t != 7\n    return 1\n"
                       "if calls != 1\n    return 2\nreturn 0\n"))
    assert run_with(compiler, "base_once", program) == 0


# The iterable is evaluated once: the loop walks the Vec `p` pointed at to begin
# with.  It's that Vec's writes it sees, not `p`'s.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_loop_doesnt_follow_a_repointed_reference(run_with, compiler):
    program = (GVEC + MAIN + FILL_V + "    var u: Vec<i32> = vec_new<i32>()\n"
               "    var p: *Vec<i32> = @v\n"
               + _body("var t: i32 = 0\nfor x in p\n    p = @u\n    t = t + x\n"
                       "if t != 7\n    return 1\nreturn 0\n"))
    assert run_with(compiler, "repoint", program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
def test_an_empty_vec_is_no_trips(run_with, compiler, it):
    program = (GVEC + MAIN + "    var v: Vec<i32> = vec_new<i32>()\n"
               + _body(f"for x in {it}\n    return 1\nreturn 0\n"))
    assert run_with(compiler, "empty", program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_vec_can_be_walked_again(run_with, compiler):
    program = (GVEC + MAIN + FILL_V + _body("var t: i32 = 0\nfor x in v\n    t = t + x\n"
                                            "for x in v\n    t = t + x\n"
                                            "return t + (v.len as i32)\n"))
    assert run_with(compiler, "again", program) == 17


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
def test_break_and_continue(run_with, compiler, it):
    program = (GVEC + MAIN + _new("i32", (1, 2, 4, 8))
               + _body(f"var t: i32 = 0\nfor x in {it}\n    if x == 2\n        continue\n"
                       "    if x == 4\n        break\n    t = t + x\n"
                       "if t != 1\n    return 1\nreturn 0\n"))
    assert run_with(compiler, "control", program) == 0


# #1685: at 16 bytes a pass, a slot left in the loop overruns the stack.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_call_results_slot_does_not_grow_the_stack(run_with, compiler):
    program = (GVEC + "fn mk() -> StrView\n    return \"ab\"\n\n" + MAIN
               + _body("var t: i32 = 0\nvar i: i32 = 0\nwhile i < 2000000\n"
                       "    for x in mk()\n        t = t + 1\n    i = i + 1\n"
                       "if t != 4000000\n    return 1\nreturn 0\n"))
    assert run_with(compiler, "stack", program) == 0


_BYTES = "var t: i32 = 0\nfor b in {it}\n    t = t + (b as i32)\nreturn t\n"
_SV = "    let s: StrView = \"ab\"\n"
_W = "struct W\n    k: i32\n    s: StrView\n\n"

# 97 + 98.
VIEWS = {
    "strview": MAIN + _SV + _body(_BYTES.format(it="s")),
    "as_bytes": MAIN + _SV + _body(_BYTES.format(it="s.as_bytes()")),
    "strview_param": ("fn f(s: StrView) -> i32\n" + _body(_BYTES.format(it="s")) + "\n" + MAIN
                      + "    return f(\"ab\")\n"),
    "strview_reference": ("fn f(s: @StrView) -> i32\n" + _body(_BYTES.format(it="s")) + "\n" + MAIN
                          + _SV + "    return f(@s)\n"),
    # Through a local, as `w.s = "ab"` is invalid IR on ritz1 (#2412).
    "strview_field": (_W + MAIN + _SV + "    var w: W\n    w.s = s\n"
                      + _body(_BYTES.format(it="w.s"))),
    "addr_of_strview_field": (_W + MAIN + _SV + "    var w: W\n    w.s = s\n"
                              + _body(_BYTES.format(it="@w.s"))),
    "as_bytes_through_a_reference": ("fn f(s: @StrView) -> i32\n"
                                     + _body(_BYTES.format(it="s.as_bytes()")) + "\n" + MAIN + _SV
                                     + "    return f(@s)\n"),
    "imported_strview": ("import ritzlib.strview\n\n" + MAIN + _SV + _body(_BYTES.format(it="s"))),
    "strview_const": "const S: StrView = \"ab\"\n\n" + MAIN + _body(_BYTES.format(it="S")),
    "string_literal": MAIN + _body(_BYTES.format(it="\"ab\"")),
    "span": ("import ritzlib.span\n\n" + MAIN + "    var a: [2]u8 = [97, 98]\n"
             "    var s: Span<u8> = span_from_ptr<u8>(@a[0], 2)\n" + _body(_BYTES.format(it="s"))),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(VIEWS))
def test_a_view_walks_its_bytes(run_with, compiler, name):
    assert run_with(compiler, name, VIEWS[name]) == 195


# ritz1 alone: ritz0 walks the global past the local (#2386), and fails to store
# the `@s` of a StrView.  The values are the programs'.
RITZ1_RUNS = {
    "a_local_hides_a_global": (_in_main("g", FILL_V + "    var g: Vec<i32> = v\n",
                                        "var g: [2]i32\n\n"), 0),
    "addr_of_strview": (MAIN + _SV + _body(_BYTES.format(it="@s")), 195),
    # 200 and its neighbour: a wide read isn't 200, and ritz0's is -56 (#2406).
    "a_byte_pointer_reads_a_byte": (GVEC + MAIN + "    var a: [2]u8 = [200, 201]\n"
                                    "    var v: Vec<*u8> = vec_new<*u8>()\n    v.push(@a[0])\n"
                                    "    var t: i32 = 0\n    for x in v\n"
                                    "        t = *x as i32\n    if t != 200\n        return 1\n"
                                    "    return 0\n", 0),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(RITZ1_RUNS))
def test_ritz1_runs(run_with, compiler, name):
    program, want = RITZ1_RUNS[name]
    assert run_with(compiler, name, program) == want


# A byte is unsigned: 200 isn't -56.  ritz0 sign-extends a `for` binding, over an
# array too (#2406), so ritz1 is pinned to what the program says.
_WIDE = (MAIN + "    var a: [2]u8 = [200, 97]\n    var s: StrView\n    s.ptr = @a[0]\n    s.len = 2\n"
         "    var t: i32 = 0\n    for b in s\n        t = t + (b as i32)\n"
         "    if t != 297\n        return 1\n    return 0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_byte_widens_unsigned(run_with, compiler):
    assert run_with(compiler, "wide", _WIDE) == 0


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2406: ritz0 sign-extends a u8 `for` binding")
def test_ritz0_a_byte_widens_unsigned(run_with):
    assert run_with("ritz0", "wide", _WIDE) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_span_of_a_wider_element(run_with, compiler):
    pre, values, check = STRUCTS["twelve_bytes"]
    program = ("import ritzlib.span\n" + GVEC + pre + MAIN + _new("S", values)
               + "    var s: Span<S> = span_from_ptr<S>(v.data, 3)\n" + _body(_walk("s", 3, check)))
    assert run_with(compiler, "span_s", program) == 0


# A user's `as_bytes` isn't the builtin one.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_users_as_bytes_is_not_a_span(compile_with, compiler):
    program = ("struct U\n    n: i32\n\nimpl U\n    fn as_bytes(self: @U) -> i32\n        return 1\n\n"
               + MAIN + "    var u: U\n    var t: i32 = 0\n    for b in u.as_bytes()\n"
               "        t = t + 1\n    return t\n")
    comp, ll, _ = compile_with(compiler, "user", program)
    _is_refused(comp, ll, UNSUPPORTED, program)


# Not a header, whatever it looks like.  ritz0 runs the first, as anything that
# opens with a pointer and an integer; ritz1 only takes the types it knows.
NOT_A_HEADER = {
    "user_struct": ("struct L\n    d: *i32\n    n: i64\n\n" + MAIN + "    var l: L\n    var t: i32 = 0\n"
                    "    for x in l\n        t = t + 1\n    return t\n"),
    "len_first": ("struct Vec<T>\n    len: i64\n    data: *T\n\n" + MAIN
                  + "    var v: Vec<i32>\n    var t: i32 = 0\n    for x in v\n"
                  "        t = t + 1\n    return t\n"),
    "narrow_len": ("struct Vec<T>\n    data: *T\n    len: i32\n\n" + MAIN
                   + "    var v: Vec<i32>\n    var t: i32 = 0\n    for x in v\n"
                   "        t = t + 1\n    return t\n"),
    "no_pointer": ("struct Vec<T>\n    len: i64\n    cap: i64\n    x: T\n\n" + MAIN
                   + "    var v: Vec<i32>\n    var t: i32 = 0\n    for x in v\n"
                   "        t = t + 1\n    return t\n"),
    "no_field": (GVEC + VH + MAIN + "    var h: VH\n    var t: i32 = 0\n    for x in h.nope\n"
                 "        t = t + 1\n    return t\n"),
    "addr_of_pointer_field": (GVEC + PH + MAIN + "    var q: PH\n    var t: i32 = 0\n"
                              "    for x in @q.p\n        t = t + 1\n    return t\n"),
    "scalar_call": ("fn mk() -> i32\n    return 1\n\n" + MAIN + "    var t: i32 = 0\n"
                    "    for x in mk()\n        t = t + 1\n    return t\n"),
    "pointer_to_pointer": (GVEC + "fn f(v: **Vec<i32>) -> i32\n    var t: i32 = 0\n    for x in v\n"
                           "        t = t + 1\n    return t\n\n" + MAIN + "    return 0\n"),
    "pointer_to_an_array_of_vecs": (GVEC + "fn f(v: *[2]Vec<i32>) -> i32\n    var t: i32 = 0\n"
                                    "    for x in v\n        t = t + 1\n    return t\n\n" + MAIN
                                    + "    return 0\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(NOT_A_HEADER))
def test_anything_else_is_refused(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, NOT_A_HEADER[name])
    _is_refused(comp, ll, UNSUPPORTED, NOT_A_HEADER[name])


ELEMENT = "this `for` element type is not supported in ritz1"
_ENUM = "enum C\n    R(i64)\n    B\n\n"
_T = "    var t: i32 = 0\n    for x in {it}\n        t = t + 1\n    return t\n"

# Refused, not guessed at.  ritz0 runs these.  An element Vec has no struct for
# (#2411) is refused as an iterable, and one that it can't name as an element.
REFUSED_ELEMENTS = {
    "enum": (GVEC + _ENUM + MAIN + "    var v: Vec<C> = vec_new<C>()\n" + _T.format(it="v"),
             UNSUPPORTED),
    "addr_of_enum": (GVEC + _ENUM + MAIN + "    var v: Vec<C> = vec_new<C>()\n"
                     + _T.format(it="@v"), UNSUPPORTED),
    "option": (GVEC + "import ritzlib.option\n\n" + MAIN
               + "    var v: Vec<Option<i32>> = vec_new<Option<i32>>()\n" + _T.format(it="v"),
               ELEMENT),
    "array": (GVEC + MAIN + "    var v: Vec<[2]i32> = vec_new<[2]i32>()\n" + _T.format(it="v"),
              UNSUPPORTED),
    "usize": (GVEC + MAIN + "    var v: Vec<usize> = vec_new<usize>()\n" + _T.format(it="v"),
              ELEMENT),
    "pointer_to_an_array": ("struct Vec<T>\n    data: *[2]i32\n    len: i64\n\n" + MAIN
                            + "    var v: Vec<i32>\n" + _T.format(it="v"), ELEMENT),
    "pointer_to_void": ("struct Vec<T>\n    data: *void\n    len: i64\n\n" + MAIN
                        + "    var v: Vec<i32>\n" + _T.format(it="v"), ELEMENT),
    "pointer_to_a_pointer": (GVEC + MAIN + "    var v: Vec<**i32> = vec_new<**i32>()\n"
                             + _T.format(it="v"), ELEMENT),
    "pointer_to_a_pointer_to_a_struct": (GVEC + "struct S\n    a: i64\n\n" + MAIN
                                         + "    var v: Vec<**S> = vec_new<**S>()\n"
                                         + _T.format(it="v"), ELEMENT),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED_ELEMENTS))
def test_an_element_ritz1_cant_name_is_refused(compile_with, compiler, name):
    program, message = REFUSED_ELEMENTS[name]
    comp, ll, _ = compile_with(compiler, name, program)
    _is_refused(comp, ll, message, program)


# Refused for now, at the iterable; ritz0 runs these (#2410, #2411).  `@v` of a
# reference is on neither ticket: ritz0 refuses it, and `:&` is #2314.
REFUSED_HOLDERS = {
    "generic_struct_field": (GVEC + "struct B<T>\n    k: i32\n    v: Vec<T>\n\n"
                             "fn f<T>(b: @B<T>) -> i32\n" + _T.format(it="b.v") + "\n" + MAIN
                             + "    var b: B<i32>\n    b.v = vec_new<i32>()\n"
                             "    return f<i32>(@b)\n"),
    "deref": GVEC + MAIN + FILL_V + "    var p: *Vec<i32> = @v\n" + _T.format(it="*p"),
    "index": GVEC + MAIN + "    var vs: [2]Vec<i32>\n" + _T.format(it="vs[1]"),
    "addr_of_index": GVEC + MAIN + "    var vs: [2]Vec<i32>\n" + _T.format(it="@vs[1]"),
    "addr_of_reference": (GVEC + "fn f(v: @Vec<i32>) -> i32\n" + _T.format(it="@v") + "\n" + MAIN
                          + FILL_V + "    return f(@v)\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED_HOLDERS))
def test_a_holder_ritz1_doesnt_reach_is_refused(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, REFUSED_HOLDERS[name])
    _is_refused(comp, ll, UNSUPPORTED, REFUSED_HOLDERS[name])
