#!/usr/bin/env python3
"""The const folders' `/`, `%` and `<` `<=` `>` `>=` are unsigned when an
operand is a u64 (#3062).

#2361 made the runtime operators follow the operand shape; #2356 made the
folders do so for `>>` only. The other operators still folded signed:

    const C: u64 = 0xFFFFFFFFFFFFFFF8
    const D: u64 = C / 3     ritz1: -2   (want 6148914691236517202)
    const E: u64 = C % 10    ritz1: -8   (want 8)
    const C: u64 = ~7        ritz0: the same, as it holds this C as -8

Every expected value comes from `_fold`: the operation is unsigned when either
operand is a u64, else signed and truncating. The i64 and u32 rows are controls
that must stay as they were.
"""

import pytest
from test_right_shift import _indent, _rename, _run, _wrap

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

U64 = (1 << 64) - 8

# name -> (const C's type, its initializer, its value). Two u64 spellings:
# ritz0 holds a hex literal as 2^64 - 8 and `~7` as -8.
SOURCES = {
    "u64_hex": ("u64", "0xFFFFFFFFFFFFFFF8", U64),
    "u64_not": ("u64", "~7", U64),
    "u64_cast": ("u64", "(0 - 8) as u64", U64),
    "i64": ("i64", "-8", -8),
    "u32": ("u32", "0xFFFFFFF8", (1 << 32) - 8),
}

# name -> (expression over C, operator, left, right; `C` stands for C's value).
EXPRS = {
    "div": ("C / 3", "/", "C", 3),
    "mod": ("C % 10", "%", "C", 10),
    "rdiv": ("9 / C", "/", 9, "C"),
    "rmod": ("9 % C", "%", 9, "C"),
    "gt": ("(C > 1) as i64", ">", "C", 1),
    "ge": ("(C >= 1) as i64", ">=", "C", 1),
    "lt": ("(C < 1) as i64", "<", "C", 1),
    "le": ("(C <= 1) as i64", "<=", "C", 1),
    "rlt": ("(1 < C) as i64", "<", 1, "C"),
}


def _trunc_div(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def _fold(op, a, b):
    """`op` on two values already in their type's range."""
    if op == "/":
        return _trunc_div(a, b)
    if op == "%":
        return a - b * _trunc_div(a, b)
    return int({">": a > b, ">=": a >= b, "<": a < b, "<=": a <= b}[op])


def _rows():
    rows = []
    for src, (ty, init, value) in SOURCES.items():
        for name, (text, op, left, right) in EXPRS.items():
            want = _fold(op, value if left == "C" else left, value if right == "C" else right)
            slot = "i64" if op not in "/%" else ty
            rows.append((f"{src}.{name}", f"const C: {ty} = {init}\nconst D: {slot} = {text}\n",
                         _wrap(want, 64, True)))
    # The ticket's two consts, by name.
    rows.append(("ticket", "const C: u64 = 0xFFFFFFFFFFFFFFF8\nconst E: u64 = C % 10\n"
                 "const D: u64 = C / 3 + E\n", 6148914691236517202 + 8))
    # A literal only a u64 can hold makes the fold unsigned.
    rows.append(("literal", "const D: u64 = 0xFFFFFFFFFFFFFFF8 % 10\n", 8))
    return rows


def _program(rows):
    """Exit 0, or the 1-based index of the first row whose D is wrong."""
    parts, calls = [], []
    for i, (_, top, want) in enumerate(rows, 1):
        for word in ("C", "D", "E"):
            top = _rename(top, word, f"{word}{i}")
        parts.append(f"{top}fn t{i}() -> i64\n{_indent(f'D{i} as i64')}")
        calls.append(f"    if t{i}() != {want}\n        return {i}\n")
    return "".join(parts) + "fn main() -> i32\n" + "".join(calls) + "    0\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_const_folds_follow_the_operand_type(request, compiler, tmp_path):
    rows = _rows()
    code = _run(request, compiler, tmp_path, _program(rows))
    wrong = rows[code - 1][0] if 0 < code <= len(rows) else code
    assert code == 0, f"{compiler}: {wrong}"


@pytest.mark.unit
def test_the_oracle_is_the_rule():
    """The u64 rows are not the i64 rows: the table can tell the two apart."""
    rows = dict((name, want) for name, _, want in _rows())
    assert rows["u64_hex.div"] == 6148914691236517202 and rows["i64.div"] == -2
    assert rows["u64_not.mod"] == 8 and rows["i64.mod"] == -8
    assert rows["u64_cast.rmod"] == 9 and rows["i64.rmod"] == 1
    assert rows["u64_hex.gt"] == 1 and rows["i64.gt"] == 0
