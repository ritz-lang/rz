#!/usr/bin/env python3
"""`==` and `!=` read a narrow operator value at its type (#3063).

A register holds an i64, so with `a: u8 = 200` the sum `a + a` sits in it as
400. #2361 brings such a value back to its type before `/`, `%` and the ordered
compares on ritz1; `==` and `!=` still read the whole register, so
`(a + a) == 144` was false there (ritz0 says true, as the spec does).

One row per operator that can leave the type's range (`+`, `-`, `*`, `<<`) on
operands of one narrow type, compared both ways (`==`, `!=`) against a
literal, against a narrow value on either side, and against another operator
form. Expected
values come from `_wrap`, the type's value on Python integers, which is also
what ritz0 answers.
"""

import pytest
from test_right_shift import _indent, _run, _wrap

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

TYPES = [("u8", 8, False), ("u16", 16, False), ("u32", 32, False),
         ("i8", 8, True), ("i16", 16, True), ("i32", 32, True)]


def _forms(bits, signed):
    """name -> (expression, its value on Python integers). Every one leaves
    the type's range before it is brought back."""
    if signed:
        a, c = -(1 << (bits - 1)) + 28, (1 << (bits - 1)) - 28   # i8: -100, 100
    else:
        a, c = (1 << bits) - 56, 56                              # u8: 200, 56
    return a, c, {
        "sum": ("(a + a)", a + a),
        "difference": ("(c - a)", c - a),
        "product": ("(a * k)", a * 3),
        "shift": ("(a << n)", a << 1),
    }


def _rows():
    """(name, declarations, condition, whether it holds)."""
    rows = []
    for ty, bits, signed in TYPES:
        a, c, forms = _forms(bits, signed)
        for name, (x, raw) in forms.items():
            want = _wrap(raw, bits, signed)
            other = _wrap(want + 1, bits, signed)
            # `w + d + d` is w once brought back, and outside the range before.
            half = -(1 << (bits - 1)) if signed else 1 << (bits - 1)
            decl = (f"let a: {ty} = {a}\nlet c: {ty} = {c}\nlet k: {ty} = 3\n"
                    f"let n: {ty} = 1\nlet w: {ty} = {want}\nlet d: {ty} = {half}\n")
            tag = f"{ty}.{name}"
            rows += [
                (f"{tag}.eq_literal", decl, f"{x} == {want}", True),
                (f"{tag}.ne_literal", decl, f"{x} != {want}", False),
                (f"{tag}.ne_other", decl, f"{x} != {other}", True),
                (f"{tag}.eq_value", decl, f"{x} == w", True),
                (f"{tag}.ne_value", decl, f"{x} != w", False),
                # The form on the right.
                (f"{tag}.value_eq", decl, f"w == {x}", True),
                (f"{tag}.value_ne", decl, f"w != {x}", False),
                # Both sides operator forms out of range, by different amounts.
                (f"{tag}.eq_form", decl, f"{x} == (w + d + d)", True),
                (f"{tag}.ne_form", decl, f"{x} != (w + d + d)", False),
            ]
        # A literal operand is an i64 and the wider operand wins, so this
        # form is not brought back: only an all-narrow one is.
        rows.append((f"{ty}.literal_widens", f"let a: {ty} = {a}\n", f"(a * 3) == {a * 3}", True))
    return rows


def _program(rows):
    """Exit 0, or the 1-based index of the first row that answers wrong."""
    parts, calls = [], []
    for i, (_, decl, cond, holds) in enumerate(rows, 1):
        body = f"{decl}if {cond}\n    return 1\n0"
        parts.append(f"fn t{i}() -> i64\n{_indent(body)}")
        calls.append(f"    if t{i}() != {int(holds)}\n        return {i}\n")
    return "".join(parts) + "fn main() -> i32\n" + "".join(calls) + "    0\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_narrow_operator_forms_compare_at_their_type(request, compiler, tmp_path):
    rows = _rows()
    assert len(rows) < 255
    code = _run(request, compiler, tmp_path, _program(rows))
    wrong = rows[code - 1][0] if 0 < code <= len(rows) else code
    assert code == 0, f"{compiler}: {wrong}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ticket(request, compiler, tmp_path):
    source = "fn main() -> i32\n" + _indent("let a: u8 = 200\nif (a + a) == 144\n    return 3\n4")
    assert _run(request, compiler, tmp_path, source) == 3


def test_the_oracle_leaves_the_range():
    """Every form's raw value is outside its type, so each row can fail."""
    for ty, bits, signed in TYPES:
        _, _, forms = _forms(bits, signed)
        for name, (_, raw) in forms.items():
            assert _wrap(raw, bits, signed) != raw, (ty, name)
    assert _wrap(400, 8, False) == 144
