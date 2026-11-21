"""Regression tests for AGAST #4283: one statement per line (LANGUAGE_SPEC §2.2).

Ritz has no `;`. ritz0 read `let a = 1 g()` as two statements, `let a = 1` and
`g()`, and compiled it; ritz1 refuses at the `g` with "unexpected 'g'". Each
REFUSED row must now fail on all three compilers at the stray token's
line:col, naming it. The ACCEPTED rows are the forms whose next statement
follows a block's DEDENT with no NEWLINE token between: they must still
compile everywhere.
"""

import pytest

from parser import ParseError, parse
from test_ritz1_move_param import _compile

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

_G = "fn g() -> i32\n    0\n\n"

# name -> (program, "line:col", message fragment)
REFUSED = {
    "let_then_call": (_G + "pub fn main() -> i32\n    let a = 1 g()\n    return 0\n",
                      "5:15", "unexpected 'g'"),
    "upper_suffix": ("pub fn main() -> i32\n    let a = 1U32\n    return 0\n",
                     "2:14", "unexpected 'U32'"),
    "call_then_call": (_G + "pub fn main() -> i32\n    g() g()\n    return 0\n",
                       "5:9", "unexpected 'g'"),
    # A literal is quoted as written, escapes and prefix included.
    "s_prefix_string": ('pub fn main() -> i32\n    let bad = s"he\\tllo"\n    return 0\n',
                        "2:16", "unexpected '\"he\\tllo\"'"),
    "let_then_cstring": ('pub fn main() -> i32\n    let a = 1 c"x"\n    return 0\n',
                         "2:15", "unexpected 'c\"x\"'"),
    "let_then_hex": ("pub fn main() -> i32\n    let a = 1 0xFF\n    return 0\n",
                     "2:15", "unexpected '0xFF'"),
    "in_one_line_arm": (_G + ("pub fn main() -> i32\n    var x: i32 = 0\n    match x\n"
                              "        0 => x = 1 g()\n        _ => x = 2\n    return x\n"),
                        "7:20", "unexpected 'g'"),
    "var_then_return": ("pub fn main() -> i32\n    var x: i32 = 1 return x\n",
                        "2:20", "unexpected 'return'"),
    "assign_then_call": (_G + ("pub fn main() -> i32\n    var x: i32 = 1\n"
                               "    x = 2 g()\n    return x\n"),
                         "6:11", "unexpected 'g'"),
    "in_if_body": (_G + ("pub fn main() -> i32\n    if true\n        let a = 1 g()\n"
                         "    return 0\n"),
                   "6:19", "unexpected 'g'"),
    "in_match_arm_block": (_G + ("pub fn main() -> i32\n    match 1\n        1 =>\n"
                                 "            let a = 2 g()\n        _ => 0\n    return 0\n"),
                           "7:23", "unexpected 'g'"),
}

# name -> program; each must compile.
ACCEPTED = {
    "after_if_block": (_G + "pub fn main() -> i32\n    var x: i32 = 0\n    if true\n"
                       "        x = 1\n    g()\n    return x\n"),
    "after_while_block": ("pub fn main() -> i32\n    var x: i32 = 0\n    while x < 3\n"
                          "        x = x + 1\n    return x\n"),
    "after_match_block": ("pub fn main() -> i32\n    var x: i32 = 0\n    match x\n"
                          "        0 => x = 1\n        _ => x = 2\n    return x\n"),
    "after_let_match": ("pub fn main() -> i32\n    let x: i32 = match 1\n        1 => 4\n"
                        "        _ => 5\n    return x\n"),
    "nested_dedent": ("pub fn main() -> i32\n    var x: i32 = 0\n    if true\n"
                      "        if true\n            x = 1\n    return x\n"),
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz0_parser_refuses(name):
    """The refusal is the parser's, at the stray token, in ritz1's words."""
    program, where, fragment = REFUSED[name]
    with pytest.raises(ParseError) as exc:
        parse(program, "main.ritz")
    line, col = where.split(":")
    assert (exc.value.span.line, exc.value.span.column) == (int(line), int(col))
    assert fragment in str(exc.value)


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_ritz0_parser_accepts(name):
    parse(ACCEPTED[name], "main.ritz")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_same_line_statement_refused(request, tmp_path, compiler, name):
    """AGAST #4283. Before the fix ritz0 compiled each."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, where, fragment = REFUSED[name]
    comp, _ = _compile(compiler, tmp_path, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} {name} compiled:\n{out[-2000:]}"
    assert f"main.ritz:{where}:" in out, f"{compiler} {name}: not at {where}:\n{out[-2000:]}"
    assert fragment in out, f"{compiler} {name}: no {fragment!r}:\n{out[-2000:]}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_statement_after_block_accepted(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll = _compile(compiler, tmp_path, ACCEPTED[name])
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} {name}:\n{out[-2000:]}"
