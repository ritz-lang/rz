"""AGAST #3388 (LARB R46, spec §2.2): ritz1 takes a deeper-indented continuation.

THE DEFECT (#2193, on ritz1)

    let h = (a or b) and
            c and d          # ritz1: unexpected indent

After a line ending in a binary operator or `as`, ritz1's lexer laid the next
line out as a block: INDENT if deeper, DEDENTs if shallower.  The grammar's
`op_nl` skips one NEWLINE after an operator (#2954, same-indent lines), but
not an INDENT.

THE RULE (R46) and ritz0's rows (test_deeper_continuation.py, #3387)

The line after one ending in a binary operator or `as` opens and closes no
block.  It must be indented at least as far as the statement's first line;
shallower is an error at that line, with ritz0's message.

THE FIX

ritz1's lexer marks the line after one that ends in an operator as a
continuation (lexer.ritz `cont_line`): no INDENT / DEDENT, and a shallower
one is refused.  ritz0 decides `>` / `>>` in its parser; ritz1's lexer
can't, so a line ending in `>` / `>>` that holds a declaration keyword (`fn`,
`struct`, `enum`, `impl`, `trait`, `type`, `extern`) ends a generic list, not
an expression, and still opens its block; elsewhere (a field `data: Vec<u8>`)
only a deeper next line continues it.

THE TESTS

One program per compiler holds ritz0's accepted rows (the two #2193
repros, `as`, an `if` condition continued then its block, a two-level dedent
after a continuation, a line shallower than an earlier continuation but not
than the statement, #2954's same-indent form) plus the `>` / `>>` split: an
operator `>` and `>>` ending a line, `fn` headers ending in `>` / `>>`, and a
struct field ending in `>` before a dedent.
The refusal row is ritz0's "shallower than the statement".
"""

import re

import pytest

from test_ref_into_value import _compile, _run

COMPILERS = ["ritz1", "ritz1_selfhosted"]

ACCEPTED = """\
struct Box<T>
    v: T

struct Holder
    b: Box<i32>

fn wrap(x: i32) -> Box<i32>
    Box { v: x }

fn unbox(b: Box<Box<i32>>) -> Box<Box<i32>>
    b

fn f(a: bool, b: bool, c: bool, d: bool) -> bool
    let h = (a or b) and
            c and d
    h

fn g(a: bool, b: bool) -> bool
    not (a or
         b)

fn widen(x: i32) -> i64
    x as
        i64

fn both(a: bool, b: bool) -> i32
    if a and
            b
        return 1
    0

fn nested(a: i32) -> i32
    if a > 0
        let t = a +
                1
        return t
    0

fn shallower(a: i32, b: i32, c: i32) -> i32
    let s = a +
                b +
        c
    s

fn same(a: i32, b: i32) -> bool
    a == 0 and
    b == 0

fn gt(a: i32, b: i32) -> bool
    a >
        b

fn shr(a: i32) -> i32
    a >>
        1

fn main() -> i32
    let bb: Box<Box<i32>> = Box { v: Box { v: 3 } }
    let h: Holder = Holder { b: wrap(5) }
    if unbox(bb).v.v != 3 or h.b.v != 5
        return 1
    if not f(true, false, true, true) or f(false, false, true, true)
        return 2
    if g(true, false) == false or g(false, false)
        return 3
    if widen(7) != 7
        return 4
    if both(true, true) != 1 or both(true, false) != 0
        return 5
    if nested(4) != 5 or nested(0) != 0
        return 6
    if shallower(1, 2, 3) != 6
        return 7
    if not same(0, 0) or same(0, 1)
        return 8
    if not gt(2, 1) or gt(1, 2)
        return 9
    if shr(8) != 4
        return 10
    3
"""

# ritz0's row: line 4 is shallower than its statement (line 3).
SHALLOWER = """\
fn f(a: i32, b: i32) -> bool
    if true
        let t = a == 0 and
    b == 0
        return t
    false

fn main() -> i32
    0
"""

CONTINUATION_MSG = ("continuation line is indented less than the statement it continues; "
                    "indent it at least as far as the statement's first line")


@pytest.mark.integration
@pytest.mark.batched
@pytest.mark.parametrize("compiler", COMPILERS)
def test_deeper_continuation_runs(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, "deeper_cont", ACCEPTED) == 3


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_shallower_than_statement_is_refused_at_that_line(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "shallower", SHALLOWER)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert ("4:1", CONTINUATION_MSG) in found, out
