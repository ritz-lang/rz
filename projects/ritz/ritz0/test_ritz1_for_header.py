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
the buffer: test_a_push_that_moves_the_buffer.  Only an rvalue gets a slot.

The programs link the real allocator: a push is what's under test, and a single
compile can't link ritzlib.gvec's `realloc`.  Each returns 0, or the number of
the first check that failed, unless it says otherwise.
"""

import atexit
import functools
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

import batching
import fast_link

import ritz0_inproc
from test_ritz1_for_iterable import (COMPILERS, MAIN, RITZ1S, SCALARS, SELFHOSTED_BIN, UNSUPPORTED,
                                     _is_refused)

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = pytest.mark.batched

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
    # Cached for the whole process, so no test owns it: remove it at exit, or
    # every gate leaves one per compiler per xdist worker in /tmp (#2875).
    atexit.register(shutil.rmtree, work, True)
    objects = []
    for unit in UNITS:
        ll = work / f"{unit}.ll"
        comp = _emit(compiler, ritz1_bin, RITZ_ROOT / "ritzlib" / f"{unit}.ritz", ll)
        assert comp.returncode == 0, comp.stdout + comp.stderr
        obj = work / f"{unit}.o"
        fast_link.clang(["clang", "-w", "-c", str(ll), "-o", str(obj)], check=True)
        objects.append(str(obj))
    return tuple(objects)


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    def go(compiler, name, program):
        batching.per_row()  # AGAST #2806
        work = tmp_path / f"{name}_{compiler}"
        work.mkdir()
        src, ll = work / "main.ritz", work / "main.ll"
        src.write_text(program)
        return _emit(compiler, ritz1_bin, src, ll), ll, work
    go.batch_compile = batch_compile(ritz1_bin)  # for batching.refused (AGAST #2806)
    return go


def _link(compiler, ritz1_bin, ll, work, extra=()):
    exe = work / "main"
    cmd = ["clang", "-w", str(ll), *_objects(compiler, ritz1_bin), *extra, "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        cmd.insert(2, str(RITZ_START))
    return fast_link.clang(cmd, cwd=work, capture_output=True, text=True), exe


def batch_build(ritz1_bin, extra=lambda compiler: ()):
    """batching.run's `build`: compile and link a batch the way `run_with` does a row.

    `extra(compiler)` names objects to link beyond the allocator's.
    """
    def build(compiler, src, work):
        ll = work / "main.ll"
        comp = _emit(compiler, ritz1_bin, src, ll)
        if comp.returncode != 0 or not ll.exists():
            return False, comp.stdout + comp.stderr, None
        link, exe = _link(compiler, ritz1_bin, ll, work, extra(compiler))
        return link.returncode == 0, link.stderr, exe
    return build


def batch_compile(ritz1_bin):
    """batching.refused's `compile`, for `compile_with`'s callers."""
    def compile(compiler, src, work):
        comp = _emit(compiler, ritz1_bin, src, work / "main.ll")
        return comp.returncode, comp.stdout + comp.stderr
    return compile


@pytest.fixture
def run_with(ritz1_bin, compile_with):
    def go(compiler, name, program):
        got = batching.run(compiler, program, batch_build(ritz1_bin),  # AGAST #2806
                           compile=batch_compile(ritz1_bin))  # #2867
        if got is not None:
            return got
        comp, ll, work = compile_with(compiler, name, program)
        assert comp.returncode == 0 and ll.exists(), (
            f"{compiler} failed on {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
        link, exe = _link(compiler, ritz1_bin, ll, work)
        assert link.returncode == 0, f"{name} would not link:\n{link.stderr[-2000:]}"
        return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    return go


def _body(text: str, indent: str = "    ") -> str:
    return "".join(indent + line + "\n" for line in text.splitlines())


def _pushes(place: str, values) -> str:
    return "".join(f"    {place}.push({v})\n" for v in values)


def _new(ty: str, values, name: str = "v") -> str:
    return f"    var {name}: Vec<{ty}> = vec_new<{ty}>()\n" + _pushes(name, values)


# Sums a `Vec<i32>`.  Seven, from 1, 2 and 4: a skipped or repeated element shows.
SUM = "var t: i32 = 0\nfor x in {it}\n    t = t + x\nif t != 7\n    return 1\nreturn 0\n"
SEED = (1, 2, 4)
FILL_V = _new("i32", SEED)
VH = "struct VH\n    k: i64\n    v: Vec<i32>\n    z: i64\n\n"
FILL_H = "    var h: VH\n    h.v = vec_new<i32>()\n" + _pushes("h.v", SEED)
OUTER = "struct O\n    n: i32\n    h: VH\n\n"
# AGAST #2411: a Vec field of a generic struct.  `B$i32` held a `%Vec$T`.
GB = "struct B<T>\n    k: i32\n    v: Vec<T>\n\n"
FILL_B = "    var b: B<i32>\n    b.v = vec_new<i32>()\n" + _pushes("b.v", SEED)
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
    "generic_call": _in_main("mk<i32>(1)", "", "fn mk<T>(a: T) -> Vec<T>\n"
                             "    var v: Vec<T> = vec_new<T>()\n    v.push(a)\n"
                             "    v.push(a + 1)\n    v.push(a + 3)\n    return v\n\n"),
    "method_call": (GVEC + "struct K\n    n: i32\n\nimpl K\n    fn mk(self: @K) -> Vec<i32>\n"
                    + _body(FILL_V, "    ") + "        return v\n\n" + MAIN
                    + "    var k: K\n" + _body(SUM.format(it="k.mk()"))),
    "field_of_a_call": _in_main("mk().v", "", VH + "fn mk() -> VH\n" + FILL_H + "    return h\n\n"),
    "generic_fn": (GVEC + "fn f<T>(v: @Vec<T>) -> i32\n" + _body(SUM.format(it="v")) + "\n" + MAIN
                   + FILL_V + "    return f<i32>(@v)\n"),
    "unannotated_reference": _in_main("r", FILL_V + "    let r = @v\n"),
    # A `let` has no storage ritz0 can name, and nothing can write to it.
    "let": _in_main("w", FILL_V + "    let w: Vec<i32> = v\n"),
    "generic_struct_field": (GVEC + GB + "fn f<T>(b: @B<T>) -> i32\n" + _body(SUM.format(it="b.v"))
                             + "\n" + MAIN + FILL_B + "    return f<i32>(@b)\n"),
    "addr_of_generic_struct_field": (GVEC + GB + "fn f<T>(b: @B<T>) -> i32\n"
                                     + _body(SUM.format(it="@b.v")) + "\n" + MAIN + FILL_B
                                     + "    return f<i32>(@b)\n"),
    "generic_struct_field_in_main": _in_main("b.v", FILL_B, GB),
    "field_of_a_let": _in_main("k.v", FILL_H + "    let k: VH = h\n", VH),
    # AGAST #2410: each walked in place.
    "deref": _in_main("*p", FILL_V + "    var p: *Vec<i32> = @v\n"),
    "array_element": _in_main("vs[1]", FILL_V + "    var vs: [2]Vec<i32>\n    vs[1] = v\n"),
    "addr_of_array_element": _in_main("@vs[1]", FILL_V + "    var vs: [2]Vec<i32>\n    vs[1] = v\n"),
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
    program = GVEC + MAIN + _new(ty, vs) + _body(_walk(it, 3, _check(ty, vs)))
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


# AGAST #2411: `usize` / `isize` are names to ritz1, not primitives, and a
# Vec<usize> had no element size.  The middle value doesn't fit 32 bits.
WORDS = {"usize": (1, 5000000000, 7), "isize": (-3, 5000000000, -70000)}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
@pytest.mark.parametrize("ty", sorted(WORDS))
def test_a_word_element_is_read_at_its_width(run_with, compiler, it, ty):
    vs = WORDS[ty]
    program = GVEC + MAIN + _new(ty, vs) + _body(_walk(it, 3, _check(ty, vs)))
    assert run_with(compiler, f"w_{ty}", program) == 0


# AGAST #2411: a Vec of a user enum.  `Vec$C` was taken for a type parameter's
# placeholder, so it had no struct.  The payload enum is 16 bytes, the unit one
# 1: each is walked at its own stride.  The weights make the order count.
UNIT_ENUM = "enum U\n    A\n    Bb\n    Cc\n\n"
PAYLOAD_ENUM = "enum C\n    R(i64)\n    B\n\n"
_FILL_U = "    var v: Vec<U> = vec_new<U>()\n" + _pushes("v", ("U.A", "U.Cc", "U.Bb"))
_FILL_C = "    var v: Vec<C> = vec_new<C>()\n" + _pushes("v", ("C.R(5)", "C.B", "C.R(7)"))
ENUM_WALKS = {
    # 1 + 30 + 200
    "unit": (UNIT_ENUM, _FILL_U, "var t: i64 = 0\nvar i: i64 = 1\nfor x in {it}\n    match x\n"
             "        U.A => t = t + i\n        U.Bb => t = t + 2 * i\n"
             "        U.Cc => t = t + 3 * i\n    i = i * 10\nif t != 231\n    return 1\n"
             "return 0\n"),
    # 5 + 200 + 21
    "payload": (PAYLOAD_ENUM, _FILL_C, "var t: i64 = 0\nvar i: i64 = 1\nfor x in {it}\n"
                "    match x\n        C.R(n) => t = t + n * i\n        C.B => t = t + 100 * i\n"
                "    i = i + 1\nif t != 226\n    return 1\nreturn 0\n"),
    # prism's shape: Vec<WindowEvent>, Vec<DrawCommand>.  A longer name was never
    # taken for a placeholder, but was walked at no stride all the same.
    "named": ("enum Event\n    Key(i32)\n    Quit\n\n",
              "    var v: Vec<Event> = vec_new<Event>()\n"
              + _pushes("v", ("Event.Key(5)", "Event.Quit", "Event.Key(7)")),
              "var t: i32 = 0\nvar i: i32 = 1\nfor x in {it}\n    match x\n"
              "        Event.Key(k) => t = t + k * i\n        Event.Quit => t = t + 100 * i\n"
              "    i = i + 1\nif t != 226\n    return 1\nreturn 0\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
@pytest.mark.parametrize("name", sorted(ENUM_WALKS))
def test_an_enum_element_is_walked_at_its_stride(run_with, compiler, it, name):
    pre, fill, walk = ENUM_WALKS[name]
    program = GVEC + pre + MAIN + fill + _body(walk.format(it=it))
    assert run_with(compiler, f"e_{name}", program) == 0


# AGAST #2411: the same, with no `for`.  Each failed to compile on ritz1 before
# any loop was involved.  The values are what ritz0 returns.
NO_LOOP = {
    "enum_vec_get": (GVEC + UNIT_ENUM + MAIN + _FILL_U + "    let g: U = vec_get<U>(@v, 1)\n"
                     "    match g\n        U.Cc => 0\n        _ => 1\n", 0),
    "enum_vec_push": (GVEC + UNIT_ENUM + MAIN + "    var v: Vec<U> = vec_new<U>()\n"
                      "    vec_push<U>(@&v, U.Bb)\n    let g: U = vec_get<U>(@v, 0)\n"
                      "    match g\n        U.Bb => 0\n        _ => 1\n", 0),
    "enum_len": (GVEC + UNIT_ENUM + MAIN + _FILL_U + "    return v.len as i32\n", 3),
    "payload_enum_vec_get": (GVEC + PAYLOAD_ENUM + MAIN + _FILL_C
                             + "    let g: C = vec_get<C>(@v, 2)\n    match g\n"
                             "        C.R(n) => n as i32\n        C.B => 100\n", 7),
    "usize_push_get_len": (GVEC + MAIN + "    var v: Vec<usize> = vec_new<usize>()\n"
                           "    v.push(5000000000)\n    v.push(7)\n"
                           "    let g: usize = vec_get<usize>(@v, 0)\n    if g != 5000000000\n"
                           "        return 1\n    return v.len as i32\n", 2),
    "generic_struct_field_len": (GVEC + GB + "fn f<T>(b: @B<T>) -> i32\n"
                                 "    return b.v.len as i32\n\n" + MAIN + FILL_B
                                 + "    return f<i32>(@b)\n", 3),
    "generic_struct_field_len_in_main": (GVEC + GB + MAIN + FILL_B + "    return b.v.len as i32\n",
                                         3),
    # Only the field names `Vec$u16`: nothing else instantiates it.
    "generic_struct_field_layout": (GVEC + GB + MAIN + "    var b: B<u16>\n    b.k = 4\n"
                                    "    return b.k\n", 4),
    "generic_struct_of_an_enum": (GVEC + UNIT_ENUM + GB + "fn f<T>(b: @B<T>) -> i32\n"
                                  "    return b.v.len as i32\n\n" + MAIN + "    var b: B<U>\n"
                                  "    b.v = vec_new<U>()\n    b.v.push(U.A)\n    b.v.push(U.Cc)\n"
                                  "    return f<U>(@b)\n", 2),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NO_LOOP))
def test_a_vec_ritz1_had_no_struct_for(run_with, compiler, name):
    program, want = NO_LOOP[name]
    assert run_with(compiler, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("it", FORMS)
def test_a_bool_element_is_a_condition(run_with, compiler, it):
    program = (GVEC + MAIN + "    var v: Vec<bool> = vec_new<bool>()\n"
               + _pushes("v", ("true", "false", "true"))
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
_GH_FILL = "    gh.v = vec_new<i32>()\n" + "".join(f"    vec_push<i32>(@&gh.v, {v})\n" for v in SEED)
_TRIPS_AT = ("var n: i32 = 0\nfor x in {it}\n    if n < 3\n        vec_push<i32>(@&{place}, x)\n"
             "    n = n + 1\nreturn n\n")


def _trips_in(sig: str, it: str, place: str, call: str, fill: str = FILL_V, pre: str = "") -> str:
    return (GVEC + pre + f"fn f({sig}) -> i32\n" + _body(_TRIPS.format(it=it, place=place)) + "\n"
            + MAIN + fill + f"    return {call}\n")


PUSHES = {
    "local": GVEC + MAIN + FILL_V + _body(_TRIPS.format(it="v", place="v")),
    "by_value_param": _trips_in("v: Vec<i32>", "v", "v", "f(v)"),
    "borrow_param": _trips_in("v:& Vec<i32>", "v", "v", "f(@&v)"),
    "mut_reference_param": _trips_in("v: @&Vec<i32>", "v", "v", "f(@&v)"),
    "pointer_param": _trips_in("v: *Vec<i32>", "v", "v", "f(@v)"),
    "field": GVEC + VH + MAIN + FILL_H + _body(_TRIPS.format(it="h.v", place="h.v")),
    "nested_field": (GVEC + VH + OUTER + MAIN + "    var o: O\n    o.h.v = vec_new<i32>()\n"
                     + _pushes("o.h.v", SEED) + _body(_TRIPS.format(it="o.h.v", place="o.h.v"))),
    "field_through_pointer": _trips_in("h: *VH", "h.v", "h.v", "f(@h)", FILL_H, VH),
    "field_through_borrow": _trips_in("h:& VH", "h.v", "h.v", "f(@&h)", FILL_H, VH),
    "field_through_two_levels": (GVEC + VH + "fn f(p: **VH, h: *VH) -> i32\n"
                                 + _body(_TRIPS.format(it="p.v", place="h.v")) + "\n" + MAIN + FILL_H
                                 + "    var q: *VH = @h\n    return f(@q, @h)\n"),
    "self_field": (GVEC + VH + "impl VH\n    fn f(self:&) -> i32\n"
                   + _body(_TRIPS.format(it="self.v", place="self.v"), " " * 8) + "\n" + MAIN
                   + FILL_H + "    return h.f()\n"),
    "global": (GVEC + "var g: Vec<i32>\n\n" + MAIN + _GLOBAL_FILL
               + _body(_TRIPS_AT.format(it="g", place="g"))),
    "global_struct_field": (GVEC + VH + "var gh: VH\n\n" + MAIN + _GH_FILL
                            + _body(_TRIPS_AT.format(it="gh.v", place="gh.v"))),
    "addr_of_local": GVEC + MAIN + FILL_V + _body(_TRIPS.format(it="@v", place="v")),
    "addr_of_field": GVEC + VH + MAIN + FILL_H + _body(_TRIPS.format(it="@h.v", place="h.v")),
    "addr_of_global": (GVEC + "var g: Vec<i32>\n\n" + MAIN + _GLOBAL_FILL
                       + _body(_TRIPS_AT.format(it="@g", place="g"))),
    "pointer_field": (GVEC + PH + MAIN + FILL_V + "    var q: PH\n    q.p = @v\n"
                      + _body(_TRIPS.format(it="q.p", place="v"))),
    "deref": (GVEC + MAIN + FILL_V + "    var p: *Vec<i32> = @v\n"
              + _body(_TRIPS.format(it="*p", place="v"))),
    "array_element": (GVEC + MAIN + FILL_V + "    var vs: [2]Vec<i32>\n    vs[1] = v\n"
                      + _body(_TRIPS.format(it="vs[1]", place="vs[1]"))),
    # AGAST #2426: a place reached through a call, a Vec or a Box.
    "vec_element": (GVEC + MAIN + FILL_V + "    var vv: Vec<Vec<i32>> = vec_new<Vec<i32>>()\n"
                    "    vv.push(v)\n" + _body(_TRIPS_AT.format(it="vv[0]", place="vv[0]"))),
    "field_of_a_pointer_call": (GVEC + VH + "var gh: VH\n\nfn mkp() -> *VH\n    return @gh\n\n"
                                + MAIN + _GH_FILL + _body(_TRIPS_AT.format(it="mkp().v", place="gh.v"))),
    "deref_of_a_call": (GVEC + "var g: Vec<i32>\n\nfn mkp() -> *Vec<i32>\n    return @g\n\n" + MAIN
                        + _GLOBAL_FILL + _body(_TRIPS_AT.format(it="*mkp()", place="g"))),
    "field_behind_a_box": (GVEC + "struct Box<T>\n    ptr: *T\n\n" + VH + MAIN + FILL_H
                           + "    var b: Box<VH>\n    b.ptr = @h\n"
                           + _body(_TRIPS.format(it="b.v", place="h.v"))),
}
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PUSHES))
def test_a_push_in_the_body_is_seen(run_with, compiler, name):
    assert run_with(compiler, name, PUSHES[name]) == 6


# AGAST #2426: `vv[i]`'s index, and the call `*mkp()` derefs, run once, before
# the loop.  The trip count, or 0 when either ran other than once.
_ONCE = "var calls: i32 = 0\n\nfn at(i: i64) -> i64\n    calls = calls + 1\n    return i\n\n"
_ONCE_TRIPS = "var n: i32 = 0\nfor x in {it}\n    n = n + 1\nif calls != 1\n    return 0\nreturn n\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name,program", [
    ("vec_element", GVEC + _ONCE + MAIN + FILL_V + "    var vv: Vec<Vec<i32>> = vec_new<Vec<i32>>()\n"
     "    vv.push(vec_new<i32>())\n    vv.push(v)\n" + _body(_ONCE_TRIPS.format(it="vv[at(1)]"))),
    ("deref_of_a_call", GVEC + _ONCE + "var g: Vec<i32>\n\nfn mkp() -> *Vec<i32>\n    at(0)\n    return @g\n\n"
     + MAIN + _GLOBAL_FILL + _body(_ONCE_TRIPS.format(it="*mkp()"))),
], ids=["vec_element", "deref_of_a_call"])
def test_what_names_the_header_runs_once(run_with, compiler, name, program):
    assert run_with(compiler, name, program) == 3


# An rvalue's header is its own: `g` growing is no write to it.  The buffer is
# still shared, so what it sees of the elements is what's there.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_call_results_header_is_its_own(run_with, compiler):
    program = (GVEC + "var g: Vec<i32>\n\nfn mk() -> Vec<i32>\n    return g\n\n" + MAIN + _GLOBAL_FILL + _body(_TRIPS_AT.format(it="mk()", place="g")))
    assert run_with(compiler, "own_header", program) == 3


# A slice is a view made there and then: a value, though it's written like a place.
_SPAN_OF_A = ("import ritzlib.span\n\n" + MAIN + "    var a: [3]i32 = [1, 2, 4]\n"
              "    var s: Span<i32> = span_from_ptr<i32>(@a[0], 3)\n    var t: i32 = 0\n"
              "    for x in s[1..3]\n        t = t + x\n    return t\n")


# ritz1 reaches it since #2726 typed a field of `s.slice(lo, hi)`'s result.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_slice_is_walked(run_with, compiler):
    assert run_with(compiler, "slice", _SPAN_OF_A) == 6


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
    "borrow_param": (GVEC + "fn f(v:& Vec<i32>) -> i32\n" + _body(_moves("v", "v")) + "\n" + MAIN
                     + _EIGHT + "    return f(@&v)\n"),
    "by_value_param": (GVEC + "fn f(v: Vec<i32>) -> i32\n" + _body(_moves("v", "v")) + "\n" + MAIN
                       + _EIGHT + "    return f(v)\n"),
    "field_through_pointer": (GVEC + VH + "fn f(h: *VH) -> i32\n" + _body(_moves("h.v", "h.v")) + "\n"
                              + MAIN + _EIGHT_H + "    return f(@h)\n"),
    "self_field": (GVEC + VH + "impl VH\n    fn f(self:&) -> i32\n"
                   + _body(_moves("self.v", "self.v"), " " * 8) + "\n" + MAIN + _EIGHT_H
                   + "    return h.f()\n"),
}


# #2387: safe, not refused.  Nothing from before the push is kept.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(MOVES))
def test_a_push_that_moves_the_buffer(run_with, compiler, name):
    assert run_with(compiler, name, MOVES[name]) == 0


# A struct element, wider than the binding's old i64 slot.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
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
@pytest.mark.parametrize("compiler", COMPILERS)
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
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_view_written_in_the_body_is_seen(run_with, compiler):
    program = (MAIN + "    var s: StrView = \"abc\"\n    let e: StrView = \"a\"\n    var n: i32 = 0\n"
               "    for b in s\n        s = e\n        n = n + 1\n    return n\n")
    assert run_with(compiler, "view", program) == 1


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_view_field_written_in_the_body_is_seen(run_with, compiler):
    program = ("struct W\n    k: i32\n    s: StrView\n\n" + MAIN
               + "    let e: StrView = \"a\"\n    var w: W\n    w.s = \"abc\"\n"
               "    var n: i32 = 0\n    for b in w.s\n        w.s = e\n        n = n + 1\n"
               "    return n\n")
    assert run_with(compiler, "view_field", program) == 1


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
@pytest.mark.parametrize("compiler", COMPILERS)
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
    "strview_field": (_W + MAIN + "    var w: W\n    w.s = \"ab\"\n"
                      + _body(_BYTES.format(it="w.s"))),
    "addr_of_strview_field": (_W + MAIN + "    var w: W\n    w.s = \"ab\"\n"
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


# ritz1 alone: ritz0 fails to store the `@s` of a StrView.  The values are the
# programs'.  A local can't take a global's name since #2407, so `for` reading a
# local over a global (#2386) is test_ritz1_for_iterable.py's refusal now.
RITZ1_RUNS = {
    "addr_of_strview": (MAIN + _SV + _body(_BYTES.format(it="@s")), 195),
    # 200 and its neighbour: a wide read isn't 200, nor a sign-extended one (#2406).
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


# A byte is unsigned: 200 isn't -56.  ritz0 sign-extended a `for` binding (#2406):
# its rows are test_ritz0_a_byte_widens_unsigned.
_WIDE = (MAIN + "    var a: [2]u8 = [200, 97]\n    var s: StrView\n    s.ptr = @a[0]\n    s.len = 2\n"
         "    var t: i32 = 0\n    for b in s\n        t = t + (b as i32)\n"
         "    if t != 297\n        return 1\n    return 0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_byte_widens_unsigned(run_with, compiler):
    assert run_with(compiler, "wide", _WIDE) == 0


# AGAST #2406: ritz0's `for` binding keeps its element's Ritz type, so a u8 widens
# with zext over each kind of iterable it walks.  ritz1's rows are above.
_A2 = "    var a: [2]u8 = [200, 201]\n"
_CHECK = "    if t != 200\n        return 1\n    return 0\n"
RITZ0_BYTES = {
    "array": MAIN + _A2 + "    var t: i32 = 0\n    for b in a\n        t = b as i32\n        break\n" + _CHECK,
    "vec": (GVEC + MAIN + "    var v: Vec<u8> = vec_new<u8>()\n    v.push(200)\n"
            "    var t: i32 = 0\n    for b in v\n        t = b as i32\n" + _CHECK),
    "array_pointer": (MAIN + _A2 + "    var p: *[2]u8 = @a\n    var t: i32 = 0\n    for b in p\n"
                      "        t = b as i32\n        break\n" + _CHECK),
    "strview": _WIDE,
    "byte_pointer": RITZ1_RUNS["a_byte_pointer_reads_a_byte"][0],
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_BYTES))
def test_ritz0_a_byte_widens_unsigned(run_with, name):
    assert run_with("ritz0", name, RITZ0_BYTES[name]) == 0


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
}


# AGAST #2410: a `*[N]Vec<T>` is a pointer to an array, whose elements are Vecs: 3 + 0.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_pointer_to_an_array_of_vecs_walks_the_vecs(run_with, compiler):
    program = (GVEC + "fn f(vs: *[2]Vec<i32>) -> i32\n    var t: i32 = 0\n    for x in vs\n"
               "        t = t + (x.len as i32) * 10 + 1\n    return t\n\n" + MAIN + FILL_V
               + "    var vs: [2]Vec<i32>\n    vs[0] = v\n    vs[1] = vec_new<i32>()\n"
               "    return f(@vs)\n")
    assert run_with(compiler, "array_of_vecs", program) == 32


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(NOT_A_HEADER))
def test_anything_else_is_refused(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, NOT_A_HEADER[name])
    _is_refused(comp, ll, UNSUPPORTED, NOT_A_HEADER[name])


_T = "    var t: i32 = 0\n    for x in {it}\n        t = t + 1\n    return t\n"


# Two pointers from the header is no iterable, however it's reached.
@pytest.mark.integration
@pytest.mark.parametrize("it,pre", [
    ("mkpp()", ""),
    ("p", "    var p: **Vec<i32> = mkpp()\n"),
    ("q.pp", "    var q: QQ\n    q.pp = mkpp()\n"),
], ids=["call", "local", "field"])
def test_ritz0_two_pointers_are_refused(compile_with, it, pre):
    program = (GVEC + "struct QQ\n    n: i32\n    pp: **Vec<i32>\n\n"
               "var g: Vec<i32>\n\nvar gp: *Vec<i32> = null\n\nfn mkpp() -> **Vec<i32>\n    gp = @g\n"
               "    return @gp\n\n" + MAIN + pre + _T.format(it=it))
    comp, ll, _ = compile_with("ritz0", "two_pointers", program)
    assert comp.returncode != 0
    assert not ll.exists()
    assert "for loop iterable not supported" in comp.stdout + comp.stderr


ELEMENT = "this `for` element type is not supported in ritz1"

# Refused, not guessed at.  ritz0 runs these.  An element Vec has no struct for
# is refused as an iterable, and one that it can't name as an element.
REFUSED_ELEMENTS = {
    "option": (GVEC + "import ritzlib.option\n\n" + MAIN
               + "    var v: Vec<Option<i32>> = vec_new<Option<i32>>()\n" + _T.format(it="v"),
               ELEMENT),
    # `Vec<[2]i32>` is `Vec$arr2_i32` since #2832 (it was a bare `Vec$`, no
    # struct, so refused as an iterable): its element is what's refused now.
    "array": (GVEC + MAIN + "    var v: Vec<[2]i32> = vec_new<[2]i32>()\n" + _T.format(it="v"),
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


# Refused, at the iterable.  `@v` of a reference is on no ticket: ritz0 refuses
# it, and `:&` is #2314.
REFUSED_HOLDERS = {
    "addr_of_reference": (GVEC + "fn f(v: @Vec<i32>) -> i32\n" + _T.format(it="@v") + "\n" + MAIN
                          + FILL_V + "    return f(@v)\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED_HOLDERS))
def test_a_holder_ritz1_doesnt_reach_is_refused(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, REFUSED_HOLDERS[name])
    _is_refused(comp, ll, UNSUPPORTED, REFUSED_HOLDERS[name])
