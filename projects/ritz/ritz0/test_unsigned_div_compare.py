#!/usr/bin/env python3
"""`/`, `%` and `<` `<=` `>` `>=` are unsigned when an operand is (#2361).

#2356 made `>>` read the shape of its left operand (`_int_shape` on ritz0,
`int_operand_shape` on ritz1); these operators kept their older test, and the
two compilers' tests were wrong on different forms. With `a: u64` holding
2^64 - 8 and `z: u64 = 0`:

    (a ^ z) > 1     ritz0: false, as `_infer_unsigned_expr` has no operator arm
    (a ^ z) / 2     ritz0: -4 (sdiv)
    K[0] / 2        ritz1: sdiv, as `get_expr_type` says i64 for a u64 element,
                    const, user method's return or `x[i].f`

Every expected value comes from `_apply`, the spec's rule on Python integers: an
operator expression has its operands' type, the wider operand winning and at
equal width the unsigned one, and the operation is unsigned when either operand
is. Signed rows pin that nothing which was signed turned unsigned.

Not here: `(a + a) == 144` with `a: u8 = 200`, a narrow sum compared before it
is brought back to its type (#2361 left it to its own ticket).
"""

import re

import pytest
from test_right_shift import _indent, _rename, _run, _wrap

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# name -> (operator text, function of the two operands). `{x}` is the form.
OPS = {
    "div": ("{x} / 3", lambda x: _trunc_div(x, 3)),
    "mod": ("{x} % 10", lambda x: _trunc_mod(x, 10)),
    "gt": ("{x} > 1", lambda x: int(x > 1)),
    "ge": ("{x} >= 1", lambda x: int(x >= 1)),
    "lt": ("{x} < 1", lambda x: int(x < 1)),
    "le": ("{x} <= 1", lambda x: int(x <= 1)),
    # The form on the right.
    "rlt": ("1 < {x}", lambda x: int(1 < x)),
    "rdiv": ("9 / {x}", lambda x: _trunc_div(9, x)),
    "rmod": ("9 % {x}", lambda x: _trunc_mod(9, x)),
}


def _trunc_div(a, b):
    """`/` truncates toward zero."""
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def _trunc_mod(a, b):
    return a - b * _trunc_div(a, b)


def _apply(op, value, bits, signed):
    """`op` on a `bits`-wide value of that signedness, as the i64 the test reads.
    The other operand is a small literal, so the form's type decides."""
    return _wrap(OPS[op][1](_wrap(value, bits, signed)), 64, True)


U64 = (1 << 64) - 8


def _u64_forms():
    """name -> (top-level items, statements, expression): every way a u64 with
    the top bit set reaches the operator, as an operator's operand or as a leaf
    ritz1's get_expr_type answers i64 for."""
    v = U64
    a = f"let a: u64 = {v}\n"
    az = a + "let z: u64 = 0\n"
    field = "struct S\n    a: u64\n"
    vec = f"var d: [1]u64 = [{v}]\nvar x = Vec<u64> {{ data: @d[0], len: 1, cap: 1 }}\n"
    return {
        "local": ("", a, "a"),
        # ritz0: an operator on the left was signed.
        "xor": ("", az, "(a ^ z)"),
        "or": ("", az, "(a | z)"),
        "and": ("", az + "let m: u64 = 0xFFFFFFFFFFFFFFFF\n", "(a & m)"),
        # `~7` and `s << 1` are 2^64 - 8 too.
        "not": ("", "let s: u64 = 7\n", "(~s)"),
        "add": ("", az, "(a + z)"),
        "literal_left": ("", a, "(1 * a)"),
        "mixed_left": ("", a + "let k: i64 = 0\n", "(k + a)"),
        "mixed_right": ("", a + "let k: i64 = 0\n", "(a + k)"),
        "shl": ("", "let s: u64 = 0x7FFFFFFFFFFFFFFC\n", "(s << 1)"),
        "nested": ("", az, "((a ^ z) | z)"),
        # ritz1: a leaf get_expr_type answered i64 for.
        "array": ("", f"var x: [2]u64 = [{v}, 0]\n", "x[0]"),
        "const": (f"const C: u64 = {v}\n", "", "C"),
        "const_array": (f"const K: [1]u64 = [{v}]\n", "", "K[0]"),
        "global_array": ("var G: [2]u64\n", f"G[0] = {v}\n", "G[0]"),
        "array_field": ("struct Q\n    x: [2]u64\n", f"var q = Q {{ x: [{v}, 0] }}\n", "q.x[0]"),
        "element_field": (field, f"var x: [1]S = [S {{ a: {v} }}]\n", "x[0].a"),
        "deref_member": (field, f"var s = S {{ a: {v} }}\nlet p: *S = @s\n", "(*p).a"),
        "method": (field + "impl S\n    fn get(self) -> u64\n        self.a\n",
                   f"let s = S {{ a: {v} }}\n", "s.get()"),
        "static_method": (field + f"impl S\n    fn mk() -> u64\n        {v}\n", "", "S.mk()"),
        "fn_pointer": (f"fn g() -> u64\n    {v}\n", "let f: fn() -> u64 = g\n", "f()"),
        "vec_index": ("", vec, "x[0]"),
        "element_xor": ("", f"var x: [1]u64 = [{v}]\nlet z: u64 = 0\n", "(x[0] ^ z)"),
    }


def _typed_forms(ty, bits, signed):
    """name -> (top, stmts, expression, its value): operator forms at `ty` with
    the top bit set. Unsigned ones must not lose it (ritz0 divided a u32 at
    i32), signed ones must keep it, and a value past the type's range, which an
    i64 register can hold, is the type's value first (as for `>>`, #2356)."""
    v = -8 if signed else (1 << bits) - 8
    a = f"let a: {ty} = {v}\nlet z: {ty} = 0\n"
    return {
        "xor": ("", a, "(a ^ z)", v),
        "or": ("", a, "(a | z)", v),
        "add": ("", a, "(a + z)", v),
        "not": ("", f"let s: {ty} = 7\n", "(~s)", ~7),
        "wrap_add": ("", a, "(a + a)", 2 * v),
    }


def _program(rows):
    """rows: list of (name, top, stmts, expr text, want). Exit 0, or the 1-based
    index of the first row whose value is wrong."""
    parts, calls = [], []
    for i, (_, top, stmts, text, want) in enumerate(rows, 1):
        for word in ("S", "G", "C", "K", "Q", "f", "g"):
            top = _rename(top, word, f"{word}{i}")
            stmts = _rename(stmts, word, f"{word}{i}")
            text = _rename(text, word, f"{word}{i}")
        body = f"{stmts}if {text}\n    return 1\n0" if _is_compare(text) else f"{stmts}({text}) as i64"
        parts.append(f"{top}fn t{i}() -> i64\n{_indent(body)}")
        calls.append(f"    if t{i}() != {want}\n        return {i}\n")
    return "import ritzlib.gvec\n" + "".join(parts) + "fn main() -> i32\n" + "".join(calls) + "    0\n"


def _is_compare(text):
    return re.search(r" (<|<=|>|>=) ", text) is not None


def _rows(forms, value, bits, signed, ops=OPS):
    rows = []
    for name, (top, stmts, x) in forms.items():
        for op in ops:
            text = OPS[op][0].format(x=x)
            want = _apply(op, value, bits, signed)
            rows.append((f"{name}.{op}", top, stmts, text, want))
    return rows


def _check(request, compiler, tmp_path, rows):
    # 255 is the most an exit code can name.
    for start in range(0, len(rows), 250):
        chunk = rows[start:start + 250]
        code = _run(request, compiler, tmp_path, _program(chunk))
        wrong = chunk[code - 1][0] if 0 < code <= len(chunk) else code
        assert code == 0, f"{compiler}: {wrong}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_way_to_reach_a_u64(request, compiler, tmp_path):
    _check(request, compiler, tmp_path, _rows(_u64_forms(), U64, 64, False))


TYPES = [("i8", 8, True), ("i64", 64, True), ("u8", 8, False), ("u32", 32, False)]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_operator_forms_keep_their_type(request, compiler, tmp_path):
    rows = []
    for ty, bits, signed in TYPES:
        for name, (top, stmts, x, value) in _typed_forms(ty, bits, signed).items():
            for op in ("div", "mod", "gt", "lt"):
                rows.append((f"{ty}.{name}.{op}", top, stmts, OPS[op][0].format(x=x),
                             _apply(op, value, bits, signed)))
    _check(request, compiler, tmp_path, rows)


def _main(body):
    return "fn main() -> i32\n" + _indent(body)


# Whole programs: name -> (source, exit code).
EXACT = {
    # The ticket's two measurements.
    "ticket_compare": (_main(f"let a: u64 = {U64}\nlet z: u64 = 0\nif (a ^ z) > 1\n    return 3\n4"), 3),
    "ticket_div": (_main(f"let a: u64 = {U64}\nlet z: u64 = 0\nlet q: u64 = (a ^ z) / 2\n"
                         f"if q == {U64 // 2}\n    return 0\n1"), 0),
    # A literal only a u64 can hold is a u64.
    "literal_past_i64": (_main("let x: i64 = 5\nif x < 0xFFFFFFFFFFFFFFF0\n    return 0\n1"), 0),
    # A signed operator expression stays signed.
    "signed_xor": (_main("let b: i64 = -8\nlet z: i64 = 0\nif (b ^ z) < 0\n    return 0\n1"), 0),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(EXACT))
def test_exact_programs(request, compiler, tmp_path, name):
    source, code = EXACT[name]
    assert _run(request, compiler, tmp_path, source) == code, f"{compiler}, {name}"


def test_the_oracle_is_the_rule():
    """`_apply` is what the tables trust, so it is checked by hand."""
    assert _apply("div", U64, 64, False) == _wrap(U64 // 3, 64, True)
    assert _apply("div", -8, 64, True) == -2
    assert _apply("mod", -8, 64, True) == -8
    assert _apply("gt", U64, 64, False) == 1
    assert _apply("gt", -8, 64, True) == 0
    assert _apply("rdiv", -8, 64, True) == -1
    assert _apply("rmod", U64, 64, False) == 9
    assert _apply("div", 248, 8, False) == 82
