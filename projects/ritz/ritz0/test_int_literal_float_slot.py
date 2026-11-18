"""An integer literal in an f32 / f64 slot takes the slot's type (AGAST #3604).

LANGUAGE_SPEC §7.5: "Integer literals are exempt: `let d: f64 = 4000000000`
and `let f: f32 = -3` need no `as`", and an argument is one of its slots.  The
emitter has always compiled these (`_int_literal_only`); the typing pass typed
the literal i64 and refused it ("argument 1 ('v'): expected f32, got i64").
Both now read the one definition of "integer literal", float_rules'
int_literal_only.  A non-literal i64 still needs `as`.
"""

import pathlib

import pytest
from parser import parse
from type_checker import TypeChecker

pytestmark = pytest.mark.unit

FNS = """
fn id_f32(v: f32) -> f32
    v

fn id_f64(v: f64) -> f64
    v

"""


def types(body: str) -> list:
    src = FNS + "fn main() -> i32\n" + "".join(f"    {line}\n" for line in body)
    return [str(e) for e in TypeChecker().check(parse(src))]


@pytest.mark.parametrize("body", [
    ["let v = id_f32(7)"],                          # the ticket's repro
    ["let v = id_f32(-3)"],                         # `-3` is UnaryOp('-', IntLit)
    ["let v = id_f64(4000000000)"],                 # inexact in f32, still a literal
    ["let v = id_f32(2 * 3)"],                      # literal arithmetic
    ["let f: f32 = -3"],                            # the spec's let examples
    ["let d: f64 = 4000000000"],
    ["let c = true", "let f: f32 = if c", "    1", "else", "    2"],  # each arm a literal
], ids=lambda body: " / ".join(line.strip() for line in body))
def test_integer_literal_takes_the_float_slot(body):
    assert types(body + ["0"]) == []


@pytest.mark.parametrize("body", [
    ["let n: i64 = 7", "let v = id_f32(n)"],
    ["let n: i64 = 7", "let f: f32 = n"],
    ["let n: i64 = 7", "let v = id_f32(n + 1)"],    # one operand is no literal
], ids=lambda body: body[-1])
def test_non_literal_i64_still_needs_as(body):
    errors = types(body + ["0"])
    assert len(errors) == 1 and "f32" in errors[0] and "i64" in errors[0], errors


def test_integer_literal_into_a_non_float_slot_is_still_judged():
    """The exemption is for a float slot: `1` into `bool` stays an error."""
    errors = types(["let b: bool = 1", "0"])
    assert errors == ["<stdin>:9:5: cannot initialize bool with i64"], errors


def test_issue_float_coercion_corpus_file_checks_clean():
    """The two findings, test_issue_float_coercion.ritz:29 and :36."""
    path = pathlib.Path(__file__).parent / "test" / "test_issue_float_coercion.ritz"
    assert [str(e) for e in TypeChecker().check(parse(path.read_text()))] == []
