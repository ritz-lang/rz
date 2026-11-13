"""AGAST #2314: `for x in @a` walks the array `a`, as `for x in a` does.

    var a: [2]i32 = [1, 3]
    var t: i32 = 0
    for x in @a             # ritz1 ran the body zero times, then refused (#2375)
        t = t + x
    return t - 1            # ritz0 3

The same for `a:& [N]T`, whose slot is the array behind the borrow (#2290), and
for `v:& Vec<T>`, whose slot holds the borrow's pointer: `@v` is that pointer
(#2286), not the slot's address.  `@&` reads the same.

`@h.a` walks the array field `h.a` in place, as `h.a` does (#2533).

`@` of a pointer or a reference, of a const, and of a call's field isn't an
iterable to ritz0, and ritz1 refuses each of them too.

Each program returns 0, or the number of the first check that failed.
"""

import subprocess

import pytest

import fast_link

import test_ritz1_for_iterable as _for_iterable
from test_ritz1_for_header import RITZ_START, _emit, _objects
from test_ritz1_for_iterable import COMPILERS, MAIN, SCALARS, _fill, _walk

# The fixtures, by name, as pytest finds them.
compile_with = _for_iterable.compile_with
run_with = _for_iterable.run_with


def _local(ty, vs, op="@"):
    return MAIN + f"    var a: [3]{ty}\n" + _fill("a", vs) + _walk(f"{op}a", ty, vs)


def _param(sig, arg, op="@"):
    def go(ty, vs):
        return (f"fn f({sig.format(ty=ty)}) -> i32\n" + _walk(f"{op}a", ty, vs) + "\n" + MAIN
                + f"    var a: [3]{ty}\n" + _fill("a", vs) + f"    return f({arg})\n")
    return go


def _global(ty, vs, op="@"):
    return f"var g: [3]{ty}\n\n" + MAIN + _fill("g", vs) + _walk(f"{op}g", ty, vs)


VEC = "struct Vec<T>\n    data: *T\n    len: i64\n\n"


def _vec(op):
    def go(ty, vs):
        # `_walk` binds `v`, so the Vec is `q`.
        return (VEC + f"fn f(q:& Vec<{ty}>) -> i32\n" + _walk(f"{op}q", ty, vs) + "\n" + MAIN
                + f"    var d: [3]{ty}\n" + _fill("d", vs)
                + f"    var v: Vec<{ty}>\n    v.data = @d[0]\n    v.len = 3\n    return f(@&v)\n")
    return go


FORMS = {
    "local": _local,
    "local_mut": lambda ty, vs: _local(ty, vs, "@&"),
    "by_value_param": _param("a: [3]{ty}", "a"),
    "borrow_param": _param("a:& [3]{ty}", "@&a"),
    "borrow_param_mut": _param("a:& [3]{ty}", "@&a", "@&"),
    "global": _global,
    "global_mut": lambda ty, vs: _global(ty, vs, "@&"),
    "borrowed_vec": _vec("@"),
    "borrowed_vec_mut": _vec("@&"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
@pytest.mark.parametrize("form", sorted(FORMS))
def test_address_of_an_iterable_walks_it(run_with, compiler, form, ty):
    assert run_with(compiler, f"{form}_{ty}", FORMS[form](ty, SCALARS[ty])) == 0


# Struct elements, with the borrow's array in between canaries: 1 + 2 + 4.
_S = "struct S\n    lo: i64\n    x: i32\n    hi: i8\n\n"
STRUCTS = {
    "borrow_param": (_S + "fn f(a:& [3]S) -> i32\n    var t: i32 = 0\n    for e in @a\n"
                     "        t = t + e.x\n    return t\n\n" + MAIN + "    var a: [3]S\n"
                     "    a[0].x = 1\n    a[1].x = 2\n    a[2].x = 4\n    return f(@&a)\n"),
    "borrowed_vec": (VEC + _S + "fn f(v:& Vec<S>) -> i32\n    var t: i32 = 0\n    for e in @v\n"
                     "        t = t + e.x\n    return t\n\n" + MAIN + "    var d: [3]S\n"
                     "    d[0].x = 1\n    d[1].x = 2\n    d[2].x = 4\n    var v: Vec<S>\n"
                     "    v.data = @d[0]\n    v.len = 3\n    return f(@&v)\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(STRUCTS))
def test_struct_elements_through_the_address(run_with, compiler, name):
    assert run_with(compiler, name, STRUCTS[name]) == 7


# The loop walks the caller's array in place (#2387): a store through the borrow
# shows on a later pass, and the caller sees it.  1 + 2 + 50.
_LIVE = ("    var t: i32 = 0\n    for x in {it}\n        {place}[2] = 50\n        t = t + x\n"
         "    return t\n")
LIVE = {
    "borrow_param": ("fn f(a:& [3]i32) -> i32\n" + _LIVE.format(it="@a", place="a") + "\n" + MAIN
                     + "    var a: [3]i32 = [1, 2, 4]\n    let t: i32 = f(@&a)\n"
                     "    if a[2] != 50\n        return 1\n    return t\n"),
    "borrowed_vec": (VEC + "fn f(v:& Vec<i32>) -> i32\n" + _LIVE.format(it="@v", place="v.data")
                     + "\n" + MAIN + "    var d: [3]i32 = [1, 2, 4]\n    var v: Vec<i32>\n"
                     "    v.data = @d[0]\n    v.len = 3\n    return f(@&v)\n"),
    "local": MAIN + "    var a: [3]i32 = [1, 2, 4]\n" + _LIVE.format(it="@a", place="a"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LIVE))
def test_a_write_in_the_body_is_seen(run_with, compiler, name):
    assert run_with(compiler, name, LIVE[name]) == 53


# `@` of something that's already a pointer is a pointer to it, not an iterable.
_MAIN_A = MAIN + "    var a: [3]i32 = [1, 2, 4]\n    return f(@a)\n"
_MAIN_V = (MAIN + "    var d: [3]i32 = [1, 2, 4]\n    var v: Vec<i32>\n    v.data = @d[0]\n"
           "    v.len = 3\n    return f(@v)\n")
_SUM = "    var t: i32 = 0\n    for x in @{n}\n        t = t + x\n    return t\n"
REFUSED = {
    "pointer_param": "fn f(a: *[3]i32) -> i32\n" + _SUM.format(n="a") + "\n" + _MAIN_A,
    "reference_param": "fn f(a: @[3]i32) -> i32\n" + _SUM.format(n="a") + "\n" + _MAIN_A,
    "pointer_to_vec": VEC + "fn f(v: *Vec<i32>) -> i32\n" + _SUM.format(n="v") + "\n" + _MAIN_V,
    "const": "const K: [3]i32 = [1, 2, 4]\n\n" + MAIN + _SUM.format(n="K"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_address_of_a_non_iterable_is_refused(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, REFUSED[name])
    assert comp.returncode != 0
    assert not ll.exists()
    if compiler != "ritz0":
        assert "this `for` iterable is not supported in ritz1" in comp.stdout + comp.stderr


# AGAST #2533: `@h.a` walks the array field `h.a` in place, as `h.a` does.  The
# member is reached once: emit_for_iterable hands what it reached to the header
# path rather than reaching it again.  Canaries either side of the array show up
# a wrong offset; i8 and i64 a stride taken from anything but the field.
def _h(ty):
    return f"struct H\n    lo: i64\n    a: [3]{ty}\n    hi: i64\n\n"


def _in_main(it, op="@", ty="i32", pre="", fill="h.a", decl="    var h: H\n", setup=""):
    vs = SCALARS[ty]
    return (_h(ty) + pre + MAIN + decl + _fill(fill, vs) + setup
            + _walk(f"{op}{it}", ty, vs))


def _field_param(sig, it, call):
    vs = SCALARS["i32"]
    return (_h("i32") + f"fn f({sig}) -> i32\n" + _walk(f"@{it}", "i32", vs) + "\n" + MAIN
            + "    var h: H\n" + _fill("h.a", vs) + f"    return {call}\n")


FIELDS = {
    "local_i8": _in_main("h.a", ty="i8"),
    "local_i64": _in_main("h.a", ty="i64"),
    "local_mut": _in_main("h.a", op="@&"),
    "nested": _in_main("o.h.a", pre="struct O\n    k: i8\n    h: H\n\n", fill="o.h.a",
                       decl="    var o: O\n"),
    "global": _in_main("g.a", pre="var g: H\n\n", fill="g.a", decl=""),
    "array_element": _in_main("hs[1].a", fill="hs[1].a", decl="    var hs: [2]H\n"),
    # AGAST #2870: an element of a `*H` call's result is a place; the call runs once.
    "element_of_a_pointer_call": _for_iterable._through_a_call("mkp()[1].a", "@"),
    "element_of_a_pointer_call_mut": _for_iterable._through_a_call("mkp()[1].a", "@&"),
    "pointer_param": _field_param("h: *H", "h.a", "f(@h)"),
    "borrow_param": _field_param("h:& H", "h.a", "f(@&h)"),
    "self": (_h("i32") + "impl H\n    fn f(self:&) -> i32\n"
             + _walk("@self.a", "i32", SCALARS["i32"], " " * 8) + "\n" + MAIN
             + "    var h: H\n" + _fill("h.a", SCALARS["i32"]) + "    return h.f()\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(FIELDS))
def test_address_of_an_array_field_walks_it(run_with, compiler, name):
    assert run_with(compiler, name, FIELDS[name]) == 0


# In place, so a store in the body shows on a later pass: 1 + 2 + 50.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", ["@", "@&"])
def test_a_write_to_the_field_in_the_body_is_seen(run_with, compiler, op):
    program = (_h("i32") + MAIN + "    var h: H\n" + _fill("h.a", (1, 2, 4))
               + _LIVE.format(it=f"{op}h.a", place="h.a"))
    assert run_with(compiler, f"live_field{op == '@&'}", program) == 53


# A call's field has no address: ritz0 says "Cannot get address of: Call".
# ritz1 refuses it before reaching the member, so the call isn't run for nothing.
_MK = "fn mk() -> O\n    var o: O\n    return o\n\n"
_O = _h("i32") + "struct O\n    h: H\n\n"
NOT_A_PLACE = {
    "field_of_a_call": _O + _MK + MAIN + _SUM.format(n="mk().h.a"),
    "field_of_a_call_mut": _O + _MK + MAIN + _SUM.format(n="mk().h.a").replace("@", "@&"),
    # A pointer field of a call's result is a field of the call too, though it
    # points at a place (#2870 lowers an index, not this).
    "pointer_field_of_a_call": ("struct P\n    p: *H\n\n" + _h("i32")
                                + "fn mk() -> P\n    var o: P\n    return o\n\n" + MAIN
                                + _SUM.format(n="mk().p.a")),
    "direct_field_of_a_call":(_h("i32") + "fn mk() -> H\n    var h: H\n    return h\n\n" + MAIN
                               + _SUM.format(n="mk().a")),
    "method_field": (_O + "impl O\n    fn mk(self:&) -> O\n        return *self\n\n" + MAIN
                     + "    var o: O\n" + _SUM.format(n="o.mk().h.a")),
    "scalar_field": _h("i32") + MAIN + "    var h: H\n" + _SUM.format(n="h.lo"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_A_PLACE))
def test_address_of_a_field_that_isnt_a_place_is_refused(compile_with, compiler, name):
    comp, ll, _ = compile_with(compiler, name, NOT_A_PLACE[name])
    assert comp.returncode != 0
    assert not ll.exists()
    if compiler != "ritz0":
        assert "this `for` iterable is not supported in ritz1" in comp.stdout + comp.stderr


# ritzlib's Vec, with its real header, borrowed and walked through `@w`.  It links
# the allocator, as test_ritz1_for_header.py does.
GVEC = ("import ritzlib.gvec\n\nfn f(w:& Vec<i32>) -> i32\n    var t: i32 = 0\n    for x in {op}w\n"
        "        t = t + x\n    return t\n\n" + MAIN
        + "    var w: Vec<i32> = vec_new<i32>()\n    w.push(1)\n    w.push(2)\n    w.push(4)\n"
        "    return f(@&w)\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", ["@", "@&"])
def test_a_borrowed_ritzlib_vec(ritz1_bin, tmp_path, compiler, op):
    src, ll, exe = tmp_path / "main.ritz", tmp_path / "main.ll", tmp_path / "main"
    src.write_text(GVEC.format(op=op))
    comp = _emit(compiler, ritz1_bin, src, ll)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    cmd = ["clang", "-w", str(ll), *_objects(compiler, ritz1_bin), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        cmd.insert(2, str(RITZ_START))
    fast_link.clang(cmd, check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == 7
