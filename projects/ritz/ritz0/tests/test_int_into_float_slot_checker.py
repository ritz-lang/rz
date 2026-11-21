"""A non-literal integer in an f32 / f64 slot, in the typing pass (AGAST #4113).

LANGUAGE_SPEC §7.5: a non-literal integer converts implicitly into a float
slot when every value of its type is exact there -- into f64: i8 i16 i32 u8
u16 u32; into f32: i8 i16 u8 u16.  The emitter applies this
(`_int_into_float_slot`, float_rules.is_exact); `--check-types` refused every
such pair ("cannot initialize f64 with u32").  Now the typing pass reads the
same table, and an inexact pair reports the emitter's words
(float_rules.int_into_float_inexact) at the value.

Integer literals are #3604's (test_int_literal_float_slot.py); the emitter's
own conversion and run results are #2945's (test_implicit_int_to_float.py).
"""

import pytest
from float_rules import int_into_float_inexact
from parser import parse
from type_checker import TypeChecker

pytestmark = pytest.mark.unit

FNS = """
struct P
    d: f64

fn id_f32(v: f32) -> f32
    v

fn id_f64(v: f64) -> f64
    v

"""
FIRST_BODY_LINE = FNS.count("\n") + 2


def types(params: str, body: list, ret: str = "i32") -> list:
    src = (FNS + f"fn f({params}) -> {ret}\n"
           + "".join(f"    {line}\n" for line in body))
    return [str(e) for e in TypeChecker().check(parse(src))]


# One row per slot site in the typing pass (each its own `_value_fits` caller),
# plus the widest exact source for each float and an if whose arms mix.
EXACT = {
    "let_u32_f64": ("x: u32", ["let d: f64 = x", "0"], "i32"),   # the ticket's repro
    "let_u16_f32": ("h: u16", ["let f: f32 = h", "0"], "i32"),
    "let_i8_f32": ("b: i8", ["let f: f32 = b", "0"], "i32"),
    "var_i16_f32": ("h: i16", ["var f: f32 = h", "0"], "i32"),
    "assign_i32_f64": ("x: i32", ["var d: f64 = 0.0", "d = x", "0"], "i32"),
    "arg_u32_f64": ("x: u32", ["let d = id_f64(x)", "0"], "i32"),
    "arg_u8_f32": ("x: u8", ["let f = id_f32(x)", "0"], "i32"),
    "return_u32_f64": ("x: u32", ["return x"], "f64"),
    "tail_u16_f32": ("x: u16", ["x"], "f32"),
    "field_i32_f64": ("x: i32", ["let p = P { d: x }", "0"], "i32"),
    "if_arms_u32_and_literal": ("x: u32, c: bool",
                                ["let d: f64 = if c", "    x", "else", "    1", "0"],
                                "i32"),
    # Literal first: the if types i64, so each arm meets the slot on its own.
    "if_arms_literal_and_u32": ("x: u32, c: bool",
                                ["let d: f64 = if c", "    1", "else", "    x", "0"],
                                "i32"),
}


@pytest.mark.parametrize("name", sorted(EXACT))
def test_exact_integer_fits_the_float_slot(name):
    params, body, ret = EXACT[name]
    assert types(params, body, ret) == []


# (params, body, return type, source type, slot type, line, column) of the value.
INEXACT = {
    "let_u64_f64": ("x: u64", ["let d: f64 = x", "0"], "i32", "u64", "f64", 0, 18),
    "let_u32_f32": ("x: u32", ["let f: f32 = x", "0"], "i32", "u32", "f32", 0, 18),
    "arg_i32_f32": ("x: i32", ["let f = id_f32(x)", "0"], "i32", "i32", "f32", 0, 20),
    "return_i64_f64": ("x: i64", ["return x"], "f64", "i64", "f64", 0, 12),
    "assign_i64_f64": ("x: i64", ["var d: f64 = 0.0", "d = x", "0"], "i32",
                       "i64", "f64", 1, 9),
    "field_u64_f64": ("x: u64", ["let p = P { d: x }", "0"], "i32", "u64", "f64", 0, 20),
}


@pytest.mark.parametrize("name", sorted(INEXACT))
def test_inexact_integer_reports_the_emitters_words(name):
    params, body, ret, src, dst, line, col = INEXACT[name]
    at = f"<stdin>:{FIRST_BODY_LINE + line}:{col}"
    assert types(params, body, ret) == [f"{at}: {int_into_float_inexact(src, dst)}"]


def test_a_float_into_an_integer_slot_is_still_refused():
    """The pair is one-way: an f64 does not fit a u32 slot."""
    errors = types("d: f64", ["let x: u32 = d", "0"])
    assert errors == [f"<stdin>:{FIRST_BODY_LINE}:5: cannot initialize u32 with f64"]
