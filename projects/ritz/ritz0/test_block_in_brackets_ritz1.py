"""AGAST #3388 (LARB R46a): no block opens inside ( [ { on ritz1.

THE RULE (R46a, spec §2.2; ritz0's side is #3429, test_block_in_brackets.py)

Inside `(`, `[` or `{` line breaks and indentation are ignored, so no block
can open there: a multi-line `if` or `match` inside brackets is an error at
the keyword, "a block can't open inside `(`: bind the `if`/`match` to a `let`
first", naming the innermost bracket.  The one-line `if c then a else b`
stays legal there, and so does its condition continued after an operator.

THE DEFECT

ritz1 refused the `(` / `[` forms with whatever the parser hit next
("unexpected end of line", "unexpected '1'"), and ACCEPTED a block `if` inside
`{` (and a `(` form whose arms ended the bracket's line): #2369's lexer
"layout frame" re-laid-out a bracket's lines after an `if` condition.

THE FIX

The frame is gone.  ritz1's lexer refuses, at the keyword, a `match` inside
brackets (it always opens a block), and an `if` inside brackets whose line
ends before its `then`, other than after an operator (the condition goes
on).  ritz0 refuses a `then` on the next line too.

THE TESTS

Each refusal row separates a path: `if` in each bracket, `match` in `(` and
`{`, and the innermost bracket named.  One program per compiler runs the
one-line forms, including a condition continued across a line after an
operator and one whose line breaks inside a bracket of its own.
"""

import re

import pytest

from test_ref_into_value import _compile, _run

COMPILERS = ["ritz1", "ritz1_selfhosted"]

_PRE = "struct P\n    x: i32\n\nfn take(x: i32) -> i32\n    x\n\n"


def _msg(bracket):
    return f"a block can't open inside `{bracket}`: bind the `if`/`match` to a `let` first"


# name: (program, "line:col" of the keyword, bracket named)
REFUSED = {
    "if_paren": (_PRE + "fn main() -> i32\n    let c: i32 = 1\n    take(if c == 1\n"
                 "        42\n    else\n        0)\n", "9:10", "("),
    "if_bracket": ("fn main() -> i32\n    let c: i32 = 1\n    let a: [1]i32 = [if c == 1\n"
                   "        42\n    else\n        0]\n    a[0]\n", "3:22", "["),
    "if_brace": (_PRE + "fn main() -> i32\n    let c: i32 = 1\n    let p: P = P { x: if c == 1\n"
                 "        42\n    else\n        0\n    }\n    p.x\n", "9:23", "{"),
    "match_paren": (_PRE + "fn main() -> i32\n    let c: i32 = 1\n    take(match c\n"
                    "        1 => 42\n        _ => 0\n    )\n", "9:10", "("),
    "match_brace": (_PRE + "fn main() -> i32\n    let c: i32 = 1\n    let p: P = P { x: match c\n"
                    "        1 => 42\n        _ => 0\n    }\n    p.x\n", "9:23", "{"),
    "innermost": (_PRE + "fn main() -> i32\n    let c: i32 = 1\n    take(P { x: if c == 1\n"
                  "        42\n    else\n        0\n    }.x)\n", "9:17", "{"),
}

ONE_LINE = _PRE + """\
fn main() -> i32
    let c: i32 = 1
    let a: i32 = take(if c == 1 then 40 else 0)
    let b: i32 = take(if c == 1 and
        c > 0 then 1 else 0)
    let p: P = P { x: if c == 0 then 0 else 1 }
    let d: i32 = take(if take(
    c) == 1 then 0 else 9)
    a + b + p.x + d
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_block_in_brackets_is_refused_at_the_keyword(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    src, where, bracket = REFUSED[name]
    comp, ll, _ = _compile(compiler, tmp_path, name, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted {name}:\n{src}\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, _msg(bracket)) in found, f"{compiler}: {name}, wanted {where}:\n{src}\n{out}"


@pytest.mark.integration
@pytest.mark.batched
@pytest.mark.parametrize("compiler", COMPILERS)
def test_one_line_if_inside_brackets_compiles(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, "one_line_if", ONE_LINE) == 42
