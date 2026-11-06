#!/usr/bin/env python3
"""A non-literal `[N]T1` fits `[N]T2` only when T1 and T2 are the same type
(LANGUAGE_SPEC §3.3, LARB ruling R5, AGAST #2343).

ritz0 used to convert element by element, and ritz1 let `[N]u32` into `[N]i32`
through because LLVM spells both `i32`. The rule holds at every store, and `as`
doesn't get round it: a conversion is a loop you write.

An array LITERAL has no element type until its slot gives it one, so the second
half of this file runs literals through the same stores and checks their values:
ritz0's conversion is gone, and it was what typed most of them.

Each row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must report
the same `line:col: message`.
"""

from types import SimpleNamespace

import pytest
from llvmlite import ir

from array_rules import ELEMENT_MISMATCH
from emitter_llvmlite import EmitError, LLVMEmitter
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _ids, _main, _run

pytestmark = pytest.mark.integration

# A fill can lower to a call to memset, and these programs link nothing else.
PRELUDE = """\
pub fn memset(dest: *u8, c: u8, n: i64) -> *u8
    var i: i64 = 0
    while i < n
        *(dest + i) = c
        i = i + 1
    dest

struct P
    x: i32

struct Q
    x: i32

struct R
    n: i32

enum E
    A
    B

"""

# `{S}` is what the value is, `{D}` the slot, `^` where the error lands.
SLOTS = {
    "argument": "fn g(b: {D}) -> i32\n    3\n\nfn f(a: {S}) -> i32\n    g(^a)\n",
    "method_argument": ("impl R\n    fn g(self: *R, b: {D}) -> i32\n        3\n\n"
                        "fn f(r: *R, a: {S}) -> i32\n    r.g(^a)\n"),
    "let": "fn f(a: {S}) -> i32\n    let b: {D} = ^a\n    3\n",
    "var": "fn f(a: {S}) -> i32\n    var b: {D} = ^a\n    3\n",
    "assign": "fn f(a: {S}) -> i32\n    var b: {D}\n    b = ^a\n    3\n",
    "store_through": "fn f(a: {S}, p: *{D}) -> i32\n    *p = ^a\n    3\n",
    "store_through_ref": "fn f(a: {S}, p: @&{D}) -> i32\n    *p = ^a\n    3\n",
    "global": "var G: {D}\n\nfn f(a: {S}) -> i32\n    G = ^a\n    3\n",
    "field": "struct H\n    b: {D}\n\nfn f(a: {S}) -> i32\n    var h: H\n    h.b = ^a\n    3\n",
    "field_through": "struct H\n    b: {D}\n\nfn f(a: {S}, h: *H) -> i32\n    h.b = ^a\n    3\n",
    "struct_literal": "struct H\n    b: {D}\n\nfn f(a: {S}) -> i32\n    var h: H = H { b: ^a }\n    3\n",
    "return": "fn f(a: {S}) -> {D}\n    return ^a\n",
    "tail": "fn f(a: {S}) -> {D}\n    ^a\n",
    "if_arm": "fn f(a: {S}, c: {D}, n: i32) -> {D}\n    if n > 0\n        ^a\n    else\n        c\n",
    "match_arm": "fn f(a: {S}, c: {D}, n: i32) -> {D}\n    match n\n        0 => ^a\n        _ => c\n",
    "element": "fn f(a: {S}) -> i32\n    var b: [1]{D} = [^a]\n    3\n",
    "cast": "fn f(a: {S}) -> i32\n    var b: {D} = ^a as {D}\n    3\n",
}

# The ticket's four, and what they stand for.
SHAPES = {
    "narrow": ("[4]i64", "[4]i32"),
    "widen": ("[4]i32", "[4]i64"),
    "float_to_int": ("[4]f64", "[4]i32"),
    "sign": ("[4]u32", "[4]i32"),
    "sign_back": ("[4]i32", "[4]u32"),
    "float_widen": ("[4]f32", "[4]f64"),
    "byte_sign": ("[4]u8", "[4]i8"),
    "bool_to_int": ("[4]bool", "[4]i8"),
    "struct": ("[4]P", "[4]Q"),
    "pointer": ("[4]*i64", "[4]*i32"),
    "struct_pointer": ("[4]*P", "[4]*Q"),
    "pointer_to_int": ("[4]*i32", "[4]i64"),
    "enum": ("[4]E", "[4]i32"),
}

# Where the array comes from: each lands in `{D}`.
SOURCES = {
    "global": "var A: {S}\n\nfn f() -> i32\n    var b: {D} = ^A\n    3\n",
    "field": "struct H\n    a: {S}\n\nfn f(h: H) -> i32\n    var b: {D} = ^h.a\n    3\n",
    "field_through": "struct H\n    a: {S}\n\nfn f(h: *H) -> i32\n    var b: {D} = ^h.a\n    3\n",
    "deref": "fn f(p: *{S}) -> i32\n    var b: {D} = ^*p\n    3\n",
    "reference": "fn f(p: @{S}) -> i32\n    var b: {D} = ^*p\n    3\n",
    "row": "fn f() -> i32\n    var m: [2]{S}\n    var b: {D} = ^m[1]\n    3\n",
    "call": "fn g(a: {S}) -> {S}\n    a\n\nfn f(a: {S}) -> i32\n    var b: {D} = ^g(a)\n    3\n",
    "method": ("impl R\n    fn g(self: *R, a: {S}) -> {S}\n        a\n\n"
               "fn f(r: *R, a: {S}) -> i32\n    var b: {D} = ^r.g(a)\n    3\n"),
    "grouped": "fn f(a: {S}) -> i32\n    var b: {D} = (^a)\n    3\n",
    "lent": "fn f(a:& {S}) -> i32\n    var b: {D} = ^a\n    3\n",
    "alias": "type A = {S}\n\nfn f(a: A) -> i32\n    var b: {D} = ^a\n    3\n",
    "generic_instance": "fn g<T>(a: [4]T) -> i32\n    var b: {D} = ^a\n    3\n\nfn f(a: {S}) -> i32\n    g<i64>(a)\n",
}


def _entry():
    return "    0\n"


def _program(template, source, dest):
    return _main(PRELUDE + template.replace("{S}", source).replace("{D}", dest), _entry())


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("shape", _ids(SHAPES))
@pytest.mark.parametrize("slot", _ids(SLOTS))
def test_every_store_refuses_another_element_type(tmp_path, compiler, slot, shape):
    source, dest = SHAPES[shape]
    _assert_refused(compiler, tmp_path, f"{slot}_{shape}", _program(SLOTS[slot], source, dest),
                    ELEMENT_MISMATCH)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("shape", ["narrow", "sign", "pointer"])
@pytest.mark.parametrize("source", _ids(SOURCES))
def test_every_source_is_judged(tmp_path, compiler, source, shape):
    from_type, dest = SHAPES[shape]
    if source == "generic_instance" and shape != "narrow":
        pytest.skip("the template instantiates at i64")
    _assert_refused(compiler, tmp_path, f"{source}_{shape}", _program(SOURCES[source], from_type, dest),
                    ELEMENT_MISMATCH)


# The rule is about the element type: these are all the same one.
SAME = {
    "plain": "fn f() -> i32\n    var a: [4]i32 = [0, 0, 0, 3]\n    var b: [4]i32 = a\n    b[3]\n",
    "alias": "type A = i32\n\nfn f() -> i32\n    var a: [4]A = [0, 0, 0, 3]\n    var b: [4]i32 = a\n    b[3]\n",
    "alias_slot": "type A = [4]i32\n\nfn f() -> i32\n    var a: [4]i32 = [0, 0, 0, 3]\n    var b: A = a\n    b[3]\n",
    "unsigned": "fn f() -> i32\n    var a: [4]u32 = [0, 0, 0, 3]\n    var b: [4]u32 = a\n    b[3] as i32\n",
    "struct": "fn f() -> i32\n    var a: [2]P\n    a[1].x = 3\n    var b: [2]P = a\n    b[1].x\n",
    "pointer": "var N: i32 = 3\n\nfn f() -> i32\n    var a: [2]*i32\n    a[1] = @N\n    var b: [2]*i32 = a\n    *b[1]\n",
    "argument": "fn g(a: [4]u8) -> i32\n    a[3] as i32\n\nfn f() -> i32\n    var a: [4]u8 = [0, 0, 0, 3]\n    g(a)\n",
    "elementwise_loop": ("fn f() -> i32\n    var a: [4]i64 = [0, 0, 0, 3]\n    var b: [4]i32\n"
                         "    for i in 0..4\n        b[i] = a[i] as i32\n    b[3]\n"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", _ids(SAME))
def test_the_same_element_type_fits(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, _main(PRELUDE + SAME[name], "    f()\n")) == 3


# ritz0 only: ritz1 has no `[4]T` param (#2305), and no float array without a type.
SAME_RITZ0 = {
    "generic": "fn g<T>(a: [4]T) -> T\n    var b: [4]T = a\n    b[3]\n\nfn f() -> i32\n    var a: [4]i32 = [0, 0, 0, 3]\n    g<i32>(a)\n",
    "inferred_float": "fn f() -> i32\n    var a = [1.5, 3.0]\n    var b: [2]f64 = a\n    b[1] as i32\n",
    "inferred_int": "fn f() -> i32\n    var a = [1, 3]\n    var b: [2]i64 = a\n    b[1] as i32\n",
    "loop_binding": ("fn f() -> i32\n    var m: [2][2]i32\n    m[1][1] = 3\n    var n: i32 = 0\n    for r in m\n"
                     "        var b: [2]i32 = r\n        n = n + b[1]\n    n\n"),
}


@pytest.mark.parametrize("name", _ids(SAME_RITZ0))
def test_the_same_element_type_fits_ritz0(tmp_path, name):
    assert _run("ritz0", tmp_path, name, _main(PRELUDE + SAME_RITZ0[name], "    f()\n")) == 3


# Literals.  `{T}` is the element type, `{L}` the literal; each program returns
# 0 only if `b[3]` is `{V}` and the array is `[N]{T}` wide, so a literal built at
# i64 and copied unconverted can't pass.
LITERAL_STORES = {
    "argument": "fn g(b: [4]{T}) -> i32\n{CHECK}    0\n\nfn f() -> i32\n    g({L})\n",
    "method_argument": ("impl R\n    fn g(self: *R, b: [4]{T}) -> i32\n{CHECK8}        0\n\n"
                        "fn f() -> i32\n    var r: R = R { n: 0 }\n    r.g({L})\n"),
    "let": "fn f() -> i32\n    let b: [4]{T} = {L}\n{CHECK}    0\n",
    "var": "fn f() -> i32\n    var b: [4]{T} = {L}\n{CHECK}    0\n",
    "assign": "fn f() -> i32\n    var b: [4]{T}\n    b = {L}\n{CHECK}    0\n",
    "store_through": ("fn s(p: *[4]{T})\n    *p = {L}\n\n"
                      "fn f() -> i32\n    var b: [4]{T}\n    s(@b)\n{CHECK}    0\n"),
    "store_through_ref": ("fn s(p: @&[4]{T})\n    *p = {L}\n\n"
                          "fn f() -> i32\n    var b: [4]{T}\n    s(@&b)\n{CHECK}    0\n"),
    "global": "var G: [4]{T}\n\nfn f() -> i32\n    G = {L}\n    var b: [4]{T} = G\n{CHECK}    0\n",
    "field": ("struct H\n    b: [4]{T}\n    tail: i32\n\n"
              "fn f() -> i32\n    var h: H\n    h.tail = 9\n    h.b = {L}\n    var b: [4]{T} = h.b\n{CHECK}"
              "    if h.tail != 9\n        return 2\n    0\n"),
    "struct_literal": ("struct H\n    b: [4]{T}\n\n"
                       "fn f() -> i32\n    var h: H = H { b: {L} }\n    var b: [4]{T} = h.b\n{CHECK}    0\n"),
    "const": "const b: [4]{T} = {L}\n\nfn f() -> i32\n{CHECK}    0\n",
}

# ritz0 only: ritz1 doesn't lower these for any array (#2302, #2305).
LITERAL_STORES_RITZ0 = {
    "return": "fn g() -> [4]{T}\n    return {L}\n\nfn f() -> i32\n    var b: [4]{T} = g()\n{CHECK}    0\n",
    "tail": "fn g() -> [4]{T}\n    {L}\n\nfn f() -> i32\n    var b: [4]{T} = g()\n{CHECK}    0\n",
    "if_value": "fn f() -> i32\n    var n: i32 = 1\n    var b: [4]{T} = if n > 0 then {L} else {L}\n{CHECK}    0\n",
    "if_assign": "fn f() -> i32\n    var n: i32 = 1\n    var b: [4]{T}\n    b = if n > 0 then {L} else {L}\n{CHECK}    0\n",
    "match_value": ("fn f() -> i32\n    var n: i32 = 1\n    var b: [4]{T} = match n\n"
                    "        1 => {L}\n        _ => {L}\n{CHECK}    0\n"),
    "match_tail": "fn g(n: i32) -> [4]{T}\n    match n\n        1 => {L}\n        _ => {L}\n\nfn f() -> i32\n    var b: [4]{T} = g(1)\n{CHECK}    0\n",
    "if_tail": "fn g(n: i32) -> [4]{T}\n    if n > 0\n        {L}\n    else\n        {L}\n\nfn f() -> i32\n    var b: [4]{T} = g(1)\n{CHECK}    0\n",
    "tuple": "fn f() -> i32\n    var t: ([4]{T}, i32) = ({L}, 1)\n    var b: [4]{T} = t.0\n{CHECK}    0\n",
    "after_a_let": ("fn f() -> i32\n    var n: i32 = 1\n    var b: [4]{T} = if n > 0\n"
                    "        let m: i32 = 2\n        {L}\n    else\n        {L}\n{CHECK}    0\n"),
    "cast": "fn f() -> i32\n    var b: [4]{T} = {L} as [4]{T}\n{CHECK}    0\n",
    "cast_with_no_slot": "fn f() -> i32\n    let b = {L} as [4]{T}\n{CHECK}    0\n",
    "alias_slot": "type A = [4]{T}\n\nfn f() -> i32\n    var b: A = {L}\n{CHECK}    0\n",
    "alias_assign": "type A = [4]{T}\n\nfn f() -> i32\n    var b: A\n    b = {L}\n{CHECK}    0\n",
}

# (element type, literal, what element 3 reads as)
LITERALS = {
    "i8": ("i8", "[0, 0, 0, -3]", "-3"),
    "u8": ("u8", "[0, 0, 0, 200]", "200"),
    "i16": ("i16", "[0, 0, 0, -300]", "-300"),
    "u32": ("u32", "[0, 0, 0, 3000000000]", "3000000000"),
    "i32": ("i32", "[0, 0, 0, -3]", "-3"),
    "i64": ("i64", "[0, 0, 0, 5000000000]", "5000000000"),
    "f32": ("f32", "[0.0, 0.0, 0.0, 1.5]", "1.5"),
    "f64": ("f64", "[0.0, 0.0, 0.0, 1.5]", "1.5"),
    "fill_i8": ("i8", "[-3; 4]", "-3"),
    "fill_u8": ("u8", "[200; 4]", "200"),
    "fill_i32": ("i32", "[7; 4]", "7"),
    "fill_f32": ("f32", "[1.5; 4]", "1.5"),
    "zero_fill_u8": ("u8", "[0; 4]", "0"),
    "zero_fill_i32": ("i32", "[0; 4]", "0"),
    "zero_fill_f32": ("f32", "[0.0; 4]", "0.0"),
}


ALIAS_READS_SIGNED = ("u8", "u32", "fill_u8")


def _literal_program(template, name):
    elem, literal, value = LITERALS[name]
    check = f"if b[3] != {value}\n"
    return _main(PRELUDE + (template.replace("{T}", elem).replace("{L}", literal)
                            .replace("{CHECK8}", f"        {check}            return 1\n")
                            .replace("{CHECK}", f"    {check}        return 1\n")), "    f()\n")


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("literal", _ids(LITERALS))
@pytest.mark.parametrize("store", _ids(LITERAL_STORES))
def test_a_literal_takes_the_slots_element_type(tmp_path, compiler, store, literal):
    if store == "const" and "f32" in literal or store == "const" and "f64" in literal:
        pytest.skip("a const array folds integers only, on any element type")
    assert _run(compiler, tmp_path, f"{store}_{literal}",
                _literal_program(LITERAL_STORES[store], literal)) == 0


@pytest.mark.parametrize("literal", _ids(LITERALS))
@pytest.mark.parametrize("store", _ids(LITERAL_STORES_RITZ0))
def test_a_literal_tail_takes_the_slots_element_type(tmp_path, store, literal):
    if store.startswith("alias") and literal in ALIAS_READS_SIGNED:
        pytest.skip("indexing an aliased unsigned array reads it signed, on any array")
    assert _run("ritz0", tmp_path, f"{store}_{literal}",
                _literal_program(LITERAL_STORES_RITZ0[store], literal)) == 0


# A literal's elements land in the slot's element type one at a time, under §7.5.
ELEMENTS = {
    "widened_element": "fn f() -> i32\n    var x: i32 = -3\n    var b: [2]i64 = [x, x]\n    b[1] as i32 + 3\n",
    "widened_fill": "fn f() -> i32\n    var x: i32 = -3\n    var b: [4]i64 = [x; 4]\n    b[3] as i32 + 3\n",
    "cast_element": "fn f() -> i32\n    var x: i64 = 3\n    var b: [2]u8 = [x as u8, 0]\n    b[0] as i32 - 3\n",
    "big_fill": "fn f() -> i32\n    var b: [100]i32 = [3; 100]\n    b[99] - 3\n",
    "big_byte_fill": "fn f() -> i32\n    var b: [100]u8 = [3; 100]\n    b[99] as i32 - 3\n",
    "big_fill_assign": "fn f() -> i32\n    var b: [100]i32\n    b = [3; 100]\n    b[99] - 3\n",
    "big_zero_fill_assign": "fn f() -> i32\n    var b: [100]i32 = [3; 100]\n    b = [0; 100]\n    b[99]\n",
    "big_fill_global": "var G: [100]u8\n\nfn f() -> i32\n    G = [3; 100]\n    G[99] as i32 - 3\n",
    "big_fill_field": ("struct H\n    b: [100]u8\n\nfn f() -> i32\n    var h: H = H { b: [3; 100] }\n"
                       "    h.b[99] as i32 - 3\n"),
    "short_literal": "fn f() -> i32\n    var b: [4]u8 = [1, 2]\n    b[1] as i32 - 2\n",
    "option_payload": "fn f() -> i32\n    var o: Option<[2]u8> = Some([0, 3])\n    0\n",
    "enum_payload": "enum Pay\n    V([2]u8)\n    N\n\nfn f() -> i32\n    var e: Pay = V([0, 3])\n    0\n",
}

# The same, on ritz0: ritz1 has no initializer for a multi-dimensional array
# (#2098) and no tuple type.
ELEMENTS_RITZ0 = {
    "nested_literal": "fn f() -> i32\n    var b: [2][2]u8 = [ [1, 2], [0, 3] ]\n    b[1][1] as i32 - 3\n",
    "nested_fill": "fn f() -> i32\n    var b: [2][2]u8 = [ [3; 2]; 2]\n    b[1][1] as i32 - 3\n",
    "nested_assign": "fn f() -> i32\n    var b: [2][2]u8\n    b = [ [1, 2], [0, 3] ]\n    b[1][1] as i32 - 3\n",
    "row_literal": "fn f() -> i32\n    var m: [2][4]u8\n    m[1] = [0, 0, 0, 3]\n    m[1][3] as i32 - 3\n",
    "tuple_fill": "fn f() -> i32\n    var u: ([2]u8, i32) = ([3; 2], 1)\n    u.0[1] as i32 - 3\n",
    "tuple_return": "fn g() -> ([2]u8, i32)\n    return ([3; 2], 1)\n\nfn f() -> i32\n    var u: ([2]u8, i32) = g()\n    u.0[1] as i32 - 3\n",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", _ids(ELEMENTS))
def test_literal_elements(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, _main(PRELUDE + ELEMENTS[name], "    f()\n")) == 0


@pytest.mark.parametrize("name", _ids(ELEMENTS_RITZ0))
def test_literal_elements_ritz0(tmp_path, name):
    assert _run("ritz0", tmp_path, name, _main(PRELUDE + ELEMENTS_RITZ0[name], "    f()\n")) == 0


# What can sit behind a store.  ritz0 finds the slot from the target, so each way
# of naming one has to get there: a literal that doesn't is built at i64 and
# refused.  `{L}` is a `[2]u8` literal, and every program returns `b[1]`'s value
# less 3.  Run on ritz0, the oracle: ritz1 doesn't lower all of these (#2304).
TARGETS = {
    "ref_let": "fn s(a:& [2]u8)\n    let p: @&[2]u8 = @&a\n    *p = {L}\n\nfn f() -> i32\n    var b: [2]u8\n    s(@&b)\n{R}",
    "ref_param": "fn s(p: @&[2]u8)\n    *p = {L}\n\nfn f() -> i32\n    var b: [2]u8\n    s(@&b)\n{R}",
    "inferred_ref": "fn f() -> i32\n    var b: [2]u8\n    let p = @&b\n    *p = {L}\n{R}",
    "inferred_ptr_call": ("fn h(p: *[2]u8) -> *[2]u8\n    p\n\nfn f() -> i32\n    var b: [2]u8\n"
                          "    let p = h(@b)\n    *p = {L}\n{R}"),
    "inferred_ref_call": ("fn h(a: @&[2]u8) -> @&[2]u8\n    a\n\nfn f() -> i32\n    var b: [2]u8\n"
                          "    let p = h(@&b)\n    *p = {L}\n{R}"),
    "call": "fn h(p: *[2]u8) -> *[2]u8\n    p\n\nfn f() -> i32\n    var b: [2]u8\n    *h(@b) = {L}\n{R}",
    "ref_call": "fn h(a: @&[2]u8) -> @&[2]u8\n    a\n\nfn f() -> i32\n    var b: [2]u8\n    *h(@&b) = {L}\n{R}",
    "method": ("struct W\n    p: *[2]u8\n\nimpl W\n    fn get(self: *W) -> *[2]u8\n        self.p\n\n"
               "fn f() -> i32\n    var b: [2]u8\n    var w: W = W { p: @b }\n    *w.get() = {L}\n{R}"),
    "global_pointer": "var P: *[2]u8\n\nfn f() -> i32\n    var b: [2]u8\n    P = @b\n    *P = {L}\n{R}",
    "pointer_field": ("struct W\n    p: *[2]u8\n\nfn f() -> i32\n    var b: [2]u8\n    var w: W = W { p: @b }\n"
                      "    *w.p = {L}\n{R}"),
    "offset": "fn s(p: *[2]u8)\n    *(p + 1) = {L}\n\nfn f() -> i32\n    var m: [2][2]u8\n    s(@m as *[2]u8)\n    var b: [2]u8 = m[1]\n{R}",
    "grouped": "fn s(p: *[2]u8)\n    *(p) = {L}\n\nfn f() -> i32\n    var b: [2]u8\n    s(@b)\n{R}",
    "cast": "fn s(p: *u8)\n    *(p as *[2]u8) = {L}\n\nfn f() -> i32\n    var b: [2]u8\n    s(@b as *u8)\n{R}",
    "pointer_pointer": "fn s(p: **[2]u8)\n    **p = {L}\n\nfn f() -> i32\n    var b: [2]u8\n    var q: *[2]u8 = @b\n    s(@q)\n{R}",
    "field_of_ref": ("struct H\n    b: [2]u8\n\nfn s(h: @&H)\n    h.b = {L}\n\n"
                     "fn f() -> i32\n    var h: H\n    s(@&h)\n    var b: [2]u8 = h.b\n{R}"),
    "field_of_lent": ("struct H\n    b: [2]u8\n\nfn s(h:& H)\n    h.b = {L}\n\n"
                      "fn f() -> i32\n    var h: H\n    s(@&h)\n    var b: [2]u8 = h.b\n{R}"),
    "field_of_deref": ("struct H\n    b: [2]u8\n\nfn s(h: *H)\n    (*h).b = {L}\n\n"
                       "fn f() -> i32\n    var h: H\n    s(@h)\n    var b: [2]u8 = h.b\n{R}"),
    "field_of_self": ("struct H\n    b: [2]u8\n\nimpl H\n    fn s(self: *H)\n        self.b = {L}\n\n"
                      "fn f() -> i32\n    var h: H\n    h.s()\n    var b: [2]u8 = h.b\n{R}"),
    "field_of_field": ("struct H\n    b: [2]u8\n\nstruct O\n    h: H\n\nfn f() -> i32\n    var o: O\n"
                       "    o.h.b = {L}\n    var b: [2]u8 = o.h.b\n{R}"),
    "field_of_element": ("struct H\n    b: [2]u8\n\nfn f() -> i32\n    var hs: [2]H\n    hs[1].b = {L}\n"
                         "    var b: [2]u8 = hs[1].b\n{R}"),
    "field_of_global": "struct H\n    b: [2]u8\n\nvar G: H\n\nfn f() -> i32\n    G.b = {L}\n    var b: [2]u8 = G.b\n{R}",
    "field_of_call": ("struct H\n    b: [2]u8\n\nfn h(p: *H) -> *H\n    p\n\nfn f() -> i32\n    var o: H\n"
                      "    h(@o).b = {L}\n    var b: [2]u8 = o.b\n{R}"),
    "generic_struct_field": ("struct W<T>\n    b: [2]T\n\nfn f() -> i32\n    var w: W<u8>\n    w.b = {L}\n"
                             "    var b: [2]u8 = w.b\n{R}"),
    "generic_fn": ("fn s<T>(p: *[2]T)\n    *p = {L}\n\nfn f() -> i32\n    var b: [2]u8\n    s<u8>(@b)\n{R}"),
    "row": "fn f() -> i32\n    var m: [2][2]u8\n    m[1] = {L}\n    var b: [2]u8 = m[1]\n{R}",
    "row_of_global": "var M: [2][2]u8\n\nfn f() -> i32\n    M[1] = {L}\n    var b: [2]u8 = M[1]\n{R}",
    "row_of_field": ("struct H\n    m: [2][2]u8\n\nfn f() -> i32\n    var h: H\n    h.m[1] = {L}\n"
                     "    var b: [2]u8 = h.m[1]\n{R}"),
    "pointer_as_array": ("fn s(p: *[2]u8)\n    p[0] = {L}\n\nfn f() -> i32\n    var b: [2]u8\n    s(@b)\n{R}"),
    "inferred_local": "fn f() -> i32\n    var a: [2]u8\n    var b = a\n    b = {L}\n{R}",
    "alias_pointer": "type A = [2]u8\n\nfn s(p: *A)\n    *p = {L}\n\nfn f() -> i32\n    var b: A\n    s(@b)\n{R}",
    "alias_field": "type A = [2]u8\n\nstruct H\n    b: A\n\nfn f() -> i32\n    var h: H\n    h.b = {L}\n    var b: [2]u8 = h.b\n{R}",
}

TARGET_VALUES = {"literal": "[0, 3]", "fill": "[3; 2]"}


@pytest.mark.parametrize("value", _ids(TARGET_VALUES))
@pytest.mark.parametrize("target", _ids(TARGETS))
def test_a_literal_finds_its_slot_through_any_target(tmp_path, target, value):
    body = (TARGETS[target].replace("{L}", TARGET_VALUES[value])
            .replace("{R}", "    b[1] as i32 - 3\n"))
    assert _run("ritz0", tmp_path, f"{target}_{value}", _main(PRELUDE + body, "    f()\n")) == 0


# A multi-dimensional array has one element type too.  ritz1 has no initializer
# or by-value param for one (#2098), so these store with `=`.
NESTED = {
    "element": "fn f() -> i32\n    var a: [2][2]i64\n    var b: [2][2]i32\n    b = ^a\n    3\n",
    "sign": "fn f() -> i32\n    var a: [2][2]u32\n    var b: [2][2]i32\n    b = ^a\n    3\n",
    "global": "var G: [2][2]i32\n\nfn f() -> i32\n    var a: [2][2]i64\n    G = ^a\n    3\n",
    "field": "struct H\n    b: [2][2]i32\n\nfn f() -> i32\n    var a: [2][2]i64\n    var h: H\n    h.b = ^a\n    3\n",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", _ids(NESTED))
def test_a_multi_dimensional_array_has_one_element_type(tmp_path, compiler, name):
    _assert_refused(compiler, tmp_path, name, _main(PRELUDE + NESTED[name], _entry()), ELEMENT_MISMATCH)


# ritz0 only: tuples, and a nested array ritz1 can't initialize.
RITZ0_REFUSED = {
    "tuple": ("fn f(t: ([2]i64, i32)) -> i32\n    var u: ([2]i32, i32) = ^t\n    3\n"),
    "tuple_sign": ("fn f(t: ([2]u32, i32)) -> i32\n    var u: ([2]i32, i32) = ^t\n    3\n"),
    "nested": "fn f(a: [2][2]i64) -> i32\n    var b: [2][2]i32 = ^a\n    3\n",
    "nested_sign": "fn f(a: [2][2]u32) -> i32\n    var b: [2][2]i32 = ^a\n    3\n",
    "inferred": "fn f() -> i32\n    var a = [1, 3]\n    var b: [2]i32 = ^a\n    3\n",
    "inferred_float": "fn f() -> i32\n    var a = [1.5, 3.0]\n    var b: [2]f32 = ^a\n    3\n",
    "literal_of_arrays": "fn f(a: [2]i64) -> i32\n    var b: [1][2]i32 = [^a]\n    3\n",
    "loop_binding": "fn f() -> i32\n    var m: [2][4]i64\n    for r in m\n        var b: [4]i32 = ^r\n    3\n",
    "loop_binding_sign": "fn f() -> i32\n    var m: [2][4]u32\n    for r in m\n        var b: [4]i32 = ^r\n    3\n",
}


@pytest.mark.parametrize("name", _ids(RITZ0_REFUSED))
def test_ritz0_refuses(tmp_path, name):
    _assert_refused("ritz0", tmp_path, name, _main(PRELUDE + RITZ0_REFUSED[name], _entry()),
                    ELEMENT_MISMATCH)


def test_the_conversion_is_gone():
    """No array branch to fall back on: a literal is built at its slot's type."""
    assert not hasattr(LLVMEmitter, "_emit_array_convert_loop")


def test_the_emitter_refuses_what_the_checker_could_not_name():
    host = SimpleNamespace(_check_bool_slot=lambda *_: None)
    value = ir.Constant(ir.ArrayType(ir.IntType(64), 4), None)
    with pytest.raises(EmitError, match="same element type"):
        LLVMEmitter._convert_type(host, value, ir.ArrayType(ir.IntType(32), 4))


# Typing a fill at its slot mustn't cost it the cheap forms: a zero or byte fill
# of an untyped literal is still a constant, whatever it is converted to.
FILL_IR = {
    "small_zero": ("var b: [16]u8 = [0; 16]", "[16 x i8] zeroinitializer"),
    "big_zero_assign": ("var b: [100]i32\n    b = [0; 100]", 'call void @"llvm.memset'),
    "big_byte_assign": ("var b: [100]u8\n    b = [3; 100]", 'call void @"llvm.memset'),
}


@pytest.mark.parametrize("name", _ids(FILL_IR))
def test_a_constant_fill_stays_cheap(tmp_path, name):
    body, wanted = FILL_IR[name]
    src = _main(PRELUDE + f"fn f() -> i32\n    {body}\n    0\n", "    f()\n")
    comp, ll, _ = _compile("ritz0", tmp_path, name, src)
    assert comp.returncode == 0, comp.stdout + comp.stderr
    assert wanted in ll.read_text()
