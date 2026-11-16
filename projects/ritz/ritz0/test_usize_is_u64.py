#!/usr/bin/env python3
"""`usize` is another name for `u64`, and `isize` for `i64` (LARB R53, #3463).

They are the same types, not new ones: ritz0 resolves the names where it reads
a type, so nothing downstream sees them. That makes `usize` unsigned for every
operator, gives it u64's literal range, and makes `Vec<usize>` and `Vec<u64>`
one instance.

Each row is one program whose `main` returns 0 when the rule holds. `b` is
2^64 - 8, so its top bit is set and a signed reading shows (`>> 60` gives -1,
`> 1` is false, `/` and `%` see -8, `as f64` is negative).

ritz1's half is #3464; it mirrors these rows by name.
"""

import pytest
from test_right_shift import _indent, _run

COMPILERS = ["ritz0"]

B = "let b = 0xFFFF_FFFF_FFFF_FFF8 as usize\n"

# name -> body of `fn main() -> i32` (top-level items first, if any).
ROWS = {
    # Unsigned operators on a `usize`.
    "shr": ("", B + "if b >> 60 != 15\n    return 1\n0"),
    "gt": ("", B + "if not (b > 1)\n    return 1\n0"),
    "div": ("", B + "if b / 2 != 0x7FFF_FFFF_FFFF_FFFC\n    return 1\n0"),
    "mod": ("", B + "if b % 10 != 8\n    return 1\n0"),
    "as_f64": ("", B + "if not (b as f64 > 0.0)\n    return 1\n0"),
    # The literal suffix is the same type.
    "suffix_shr": ("", "let b = 0xFFFF_FFFF_FFFF_FFF8usize\nif b >> 60 != 15\n    return 1\n0"),
    # u64's literal range.
    "literal_range": ("", "let a: usize = 18446744073709551608\nif a >> 60 != 15\n    return 1\n0"),
    # `sizeof` reads its operand as an expression, not a type.
    "sizeof": ("", "if sizeof(usize) != sizeof(u64) or sizeof(isize) != 8\n    return 1\n0"),
    # One instance: a fn taking `Vec<u64>` takes a `Vec<usize>`, and `isize`'s.
    "vec_usize_is_vec_u64": (
        "import ritzlib.gvec\nfn first(v: @Vec<u64>) -> u64\n    return *v.data\n",
        "var d: [1]usize = [7]\nvar x = Vec<usize> { data: @d[0], len: 1, cap: 1 }\n"
        "if first(@x) != 7\n    return 1\n0"),
    "vec_isize_is_vec_i64": (
        "import ritzlib.gvec\nfn first(v: @Vec<i64>) -> i64\n    return *v.data\n",
        "var d: [1]isize = [-7]\nvar x = Vec<isize> { data: @d[0], len: 1, cap: 1 }\n"
        "if first(@x) != -7\n    return 1\n0"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.integration
@pytest.mark.parametrize("row", ROWS)
def test_usize_is_u64(request, compiler, row, tmp_path):
    top, body = ROWS[row]
    source = top + "fn main() -> i32\n" + _indent(body)
    assert _run(request, compiler, tmp_path, source) == 0, source


def test_names_resolved_by_parser():
    """Nothing downstream sees `usize`/`isize`: the parser hands out `u64`/`i64`."""
    from lexer import Lexer
    from parser import Parser
    import ritz_ast as rast

    src = ("fn f(a: usize, b: *isize, c: [usize]) -> Vec<usize>\n"
           "    let n = sizeof(usize) + 1usize\n    return a as usize\n")
    module = Parser(Lexer(src, "t.ritz").tokenize()).parse_module()
    seen = []

    def walk(node):
        if isinstance(node, rast.NamedType):
            seen.append(node.name)
        elif isinstance(node, rast.Ident):
            seen.append(node.name)
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif hasattr(node, "__dict__"):
            for value in vars(node).values():
                if isinstance(value, (list, rast.Node)):
                    walk(value)

    walk(module)
    assert "usize" not in seen and "isize" not in seen, seen
    assert seen.count("u64") == 6 and "i64" in seen, seen


# A bare `usize`/`isize` in an expression names no value (#3573). ritz0 used to
# read it as the constant 0, a leftover from before the lexer read `0usize`
# as one token. One row per name, plus a local named `usize`, which still wins.
BARE = {
    "usize": ("let x = usize\nx as i32", "Unknown identifier: usize"),
    "isize": ("let x = 1 + isize\nx as i32", "Unknown identifier: isize"),
    "local_named_usize": ("let usize = 0\nusize", None),
}


@pytest.mark.integration
@pytest.mark.parametrize("row", BARE)
def test_bare_usize_is_undefined(row, tmp_path):
    from ritz0_inproc import run_ritz0

    body, error = BARE[row]
    src = tmp_path / "t.ritz"
    src.write_text("fn main() -> i32\n" + _indent(body))
    r = run_ritz0([src.name, "-o", "t.ll"], cwd=tmp_path)
    if error is None:
        assert r.returncode == 0, r.stderr
    else:
        assert r.returncode != 0 and error in r.stdout + r.stderr, (r.stdout, r.stderr)
